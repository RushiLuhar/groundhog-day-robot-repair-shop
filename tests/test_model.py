from types import SimpleNamespace as N
from unittest.mock import Mock
import pytest
from repair_shop.model import OpenAIModel, ModelError


def fake_model(response):
    m=OpenAIModel.__new__(OpenAIModel); m.name='configured-model'
    m.client=N(responses=N(create=Mock(return_value=response)))
    return m

def response(calls=None, status='completed'):
    return N(output=calls or [],status=status,usage=N(input_tokens=19,output_tokens=7),output_text='',id='test-response')

def test_official_adapter_single_call_and_bounds():
    m=fake_model(response([N(type='function_call',name='inspect',arguments='{}')]))
    r=m.decide({'ticket':{}})
    assert r.action=={'name':'inspect','arguments':{}} and r.input_tokens==19 and r.output_tokens==7
    kwargs=m.client.responses.create.call_args.kwargs
    assert kwargs['model']=='configured-model' and kwargs['max_output_tokens']==1024
    assert kwargs['parallel_tool_calls'] is False and kwargs['store'] is False
    assert len(kwargs['tools'])==3

def test_incomplete_or_multiple_calls_end_job_but_preserve_usage():
    c=N(type='function_call',name='inspect',arguments='{}')
    for resp in [response([c], 'incomplete'),response([c,c]),response([N(type='function_call',name='operate',arguments='broken')])]:
        r=fake_model(resp).decide({})
        assert r.action is None and r.output_tokens==7

def test_sanitized_exception_and_no_adapter_retry():
    m=fake_model(response()); m.client.responses.create.side_effect=RuntimeError('sensitive raw response')
    with pytest.raises(ModelError) as e: m.decide({})
    assert 'sensitive' not in str(e.value)
    assert m.client.responses.create.call_count==1

def test_maintenance_bound_and_usage():
    m=fake_model(response()); r=m.maintain({})
    assert m.client.responses.create.call_args.kwargs['max_output_tokens']==1600
    assert r.input_tokens==19
    assert m.client.responses.create.call_args.kwargs['text']['format']['type']=='json_schema'

def test_safe_machine_error_details_without_raw_body():
    class Rejected(Exception):
        status_code=400
        code='unsupported_parameter'
        param='text.format'
    m=fake_model(response()); m.client.responses.create.side_effect=Rejected('raw sensitive message')
    with pytest.raises(ModelError) as exc: m.maintain({})
    assert 'code=unsupported_parameter' in str(exc.value)
    assert 'param=text.format' in str(exc.value)
    assert 'raw sensitive' not in str(exc.value)


def test_per_mechanic_settings_reach_official_request():
    from repair_shop.tasks import get_suite
    m=fake_model(response([N(type='function_call',name='inspect',arguments='{}')]))
    m.reasoning='high';m.step_limit=20;m.repair_output_tokens=700;m.memory_output_tokens=900
    m.memory_tokens=600;m.tools=list(get_suite('diagnostic-v1').tools);m.task_instructions='Public task instructions'
    m.decide({})
    kwargs=m.client.responses.create.call_args.kwargs
    assert kwargs['reasoning']=={'effort':'high'} and kwargs['max_output_tokens']==700
    assert '20-step cap' in kwargs['instructions'] and 'Public task instructions' in kwargs['instructions']
    assert [x['name'] for x in kwargs['tools']]==['inspect','diagnose','operate','test']
    m.maintain({})
    kwargs=m.client.responses.create.call_args.kwargs
    assert kwargs['reasoning']=={'effort':'high'} and kwargs['max_output_tokens']==900
    assert '480 tokens' in kwargs['instructions'] and 'ROBOT family' in kwargs['instructions']


def test_learning_tools_and_output_limit_reason():
    from repair_shop.tasks import get_suite
    resp=response(status='incomplete');resp.incomplete_details=N(reason='max_output_tokens')
    m=fake_model(resp);m.tools=list(get_suite('learning-v1').tools)
    reply=m.decide({})
    assert reply.end_reason=='response output limit reached' and reply.output_tokens==7
    assert 'repair using operate' not in m.client.responses.create.call_args.kwargs['instructions']
