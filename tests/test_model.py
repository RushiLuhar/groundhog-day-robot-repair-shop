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
