"""Offline acceptance for proposal v2; no live clients or benchmark claims."""
import json,threading
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace as N
from unittest.mock import Mock
import pytest
from repair_shop.evaluation.config import EvaluationConfig,Condition,AgentConfig,preset
from repair_shop.evaluation.runner import EvaluationRun,recovered
from repair_shop.evaluation.service import ServiceWorld,ServiceDemo,suite
from repair_shop.evaluation.models import ScriptedWriter,LiveAgent
from repair_shop.evaluation.memory import Memory,EMPTY
from repair_shop.evaluation.observations import observation,tokens,supplied
from repair_shop.evaluation.storage import Store
from repair_shop.evaluation.reporting import export,render
from repair_shop.evaluation.app import Controller,build_app,describe
from repair_shop.model import Reply,ModelError


def finish(c=None,**kwargs):
    r=EvaluationRun(c or EvaluationConfig(),**kwargs);list(r.run());return r

@pytest.mark.parametrize('count',[1,2,3,4])
def test_arbitrary_paired_conditions_fresh_repetitions_and_manifest(count):
    conditions=tuple(Condition('c'+str(i),('none','rolling','structured')[i%3]) for i in range(count))
    c=EvaluationConfig(conditions=conditions,repetitions=2)
    r=finish(c)
    assert r.state=='completed' and len(r.attempts)==16*count and all(x['certified'] for x in r.attempts)
    assert [(a['repetition'],a['job'],a['condition']) for a in r.attempts]==[(rep,j,c.id) for rep in (1,2) for j in range(1,9) for c in conditions[(rep-1)%count:]+conditions[:(rep-1)%count]]
    for row in r.attempts:
        if row['job']==1:assert not row['memory_supply_audit']['supplied_ids']
        for entry in row['memory_supply_audit']['supplied_ids']:
            if row['condition'].endswith('1'):assert f'r{row["repetition"]}:{row["condition"]}:' in entry
    manifest=r.manifest;manifest['config']['conditions'][0]['repair']['model']='altered'
    assert r.manifest['config']['conditions'][0]['repair']['model']!='altered'
    assert r.manifest['log_version'] and r.manifest['source']['commit']
    assert EvaluationConfig.from_dict(json.loads(json.dumps(c.to_dict())))==c
    with pytest.raises(ValueError):list(r.run())


def test_new_suite_cold_paths_transfer_exception_healthy_and_compound():
    r=finish();rows={(x['condition'],x['job']):x for x in r.attempts}
    assert all(x['steps']<=20 for x in r.attempts)
    assert rows['none',8]['steps']==14
    for policy in ('none','rolling','structured'):
        assert not any(e['action']['name'] in ('calibrate','operate') for e in rows[policy,2]['raw_events'])
        assert sum(e['action']['name']=='sample_sensor' for e in rows[policy,6]['raw_events'])==2
        assert sum(e['action']['name']=='sample_sensor' for e in rows[policy,8]['raw_events'])==2
    for job in (3,5,7):
        assert rows['structured',job]['steps']<rows['none',job]['steps']
        assert rows['rolling',job]['steps']==rows['structured',job]['steps'] # no guaranteed structured win
    assert r.totals()['input']==r.totals()['output']==0


def test_independent_certificate_rejects_masked_heat_partial_work_and_wrong_order():
    w=ServiceWorld(suite().jobs[3]);w.call('power',{'state':'off'})
    # Physical 80-degree heat can be made to look safe on the display.
    w.call('calibrate',{'gain':4,'bias':10})
    assert w.inspect()['indicated_temperature']==40
    w.call('power',{'state':'on'});assert not w.call('test',{})['pass']
    w=ServiceWorld(suite().jobs[7]);w.call('power',{'state':'off'})
    assert not w.call('operate',{'operation':'vent'})['ok']
    assert not w.call('operate',{'operation':'seal'})['ok']
    for op in ('align','vent','seal'):assert w.call('operate',{'operation':op})['ok']
    w.call('calibrate',{'gain':4,'bias':-3});w.call('power',{'state':'on'})
    assert not w.call('test',{})['pass'] # cable remains broken
    w.call('power',{'state':'off'});w.call('operate',{'operation':'reseat_cable'});w.call('power',{'state':'on'})
    assert w.call('test',{})['pass']


def test_wrong_memory_is_fallible_and_cold_recovery_remains_possible():
    r=finish();row=next(x for x in r.attempts if x['condition']=='structured' and x['job']==7)
    old=row['memory_input'];wrong=deepcopy(old)
    for record in wrong['records']:
        if record['applicability']['origin']=='factory':record['text']=json.dumps({'calibration':{'gain':3,'bias':-5}})
    demo=ServiceDemo();world=ServiceWorld(suite().jobs[6]);logs=[]
    for step in range(20):
        action=demo.decide({'current_job_log':supplied(logs),'prior_memory':wrong}).action
        result=world.call(action['name'],action['arguments']);logs.append(observation(str(step),7,action,result))
        if world.passed:break
    assert world.passed and any(e['result'].get('pass') is False for e in logs)


def test_literal_logs_raw_ties_and_no_arithmetic_or_extra_writer_context():
    action={'name':'sample_sensor','arguments':{'level':'high'}};result={'level':'high','reference_temperature':70,'raw_reading':150}
    entry=observation('e3',1,action,result)
    assert entry['result']==result and '150' in entry['text'] and '70' in entry['text']
    assert 'gain' not in entry['text'] and 'bias' not in entry['text']
    assert entry['entry_id']=='e3' and entry['job']==1
    with pytest.raises(ValueError):observation('e',1,{'name':'hidden','arguments':{}},result)
    with pytest.raises(ValueError):observation('e',1,action,{**result,'target_gain':2})
    with pytest.raises(ValueError):observation('e',1,{'name':'test','arguments':{}},{'pass':False,'observation':'x'*3000})
    seen=[]
    class Writer(ScriptedWriter):
        def write(self,p):seen.append(deepcopy(p));return super().write(p)
    r=finish(agent_factory=lambda a,role,s:ServiceDemo() if role=='repair' else Writer())
    assert len(seen)==8
    assert set(seen[0])=={'ticket','observation_log','missing_entries','previous_records','source_catalog','retention_token_limit'}
    assert not any(k in json.dumps(seen) for k in ('target_gain','target_bias','align_first','initial_gain','fixture_data'))
    for row in r.attempts:
        assert len(row['raw_events'])==len(row['observation_log'])
        for raw,log in zip(row['raw_events'],row['observation_log']):
            assert raw=={k:log[k] for k in raw}
            assert log==observation(raw['entry_id'],raw['job'],raw['action'],raw['result'])


def test_rolling_whole_entries_partial_boundaries_and_structured_budget_audits():
    r=finish();row=r.attempts[0];entries=row['observation_log'];m=Memory();m.observe(entries)
    c=Condition('rolling','rolling',rolling_entry_limit=2,retention_tokens=1000,supply_tokens=1000)
    audit=m.retain_rolling(entries,c);context,supply=m.supply(c)
    assert context==supplied(entries[-2:]) and supply['partial_jobs']==[1] and len(audit['evicted_ids'])==len(entries)-2
    c=Condition('structured','structured',retention_tokens=128,supply_tokens=128)
    good={'kind':'semantic','applicability':{'component':'TS-7','revision':'R1','origin':'factory'},
          'source_entries':[entries[0]['entry_id'],entries[-1]['entry_id']],'status':'test-supported','text':'Observed a passing sensor calibration.'}
    bad={**good,'source_entries':['future']}
    audit=m.merge(json.dumps({'records':[good,bad]}),c)
    assert audit['rejected'] and audit['retained_ids'] and tokens({'records':m.records})<=128
    retained=deepcopy(m.records);m.merge(json.dumps(EMPTY),c);assert m.records==retained
    duplicate={**good,'source_entries':[entries[-1]['entry_id']]}
    audit=m.merge(json.dumps({'records':[duplicate]}),c);assert audit['deduplicated_ids']
    audit=m.merge(json.dumps({'records':[{**good,'text':'long '*1000}]}),c);assert audit['rejected']
    context,audit=m.supply(c);assert tokens(context)<=128 and audit['supplied_ids']
    uncertain={**good,'source_entries':[entries[0]['entry_id']]}
    assert m.merge(json.dumps({'records':[uncertain]}),c)['rejected']


def test_log_failure_keeps_raw_ground_truth_and_missing_marker():
    def broken(*args):raise ValueError('unsupported result')
    r=finish(renderer=broken)
    row=r.attempts[0]
    assert r.state=='error' and row['logging_error'] and len(row['raw_events'])==1
    assert row['missing_entries'] and not row['observation_log']
    assert all(x['status']=='unattempted' for x in r.attempts[1:])

class Metered(ServiceDemo):
    def decide(self,c):
        r=super().decide(c);r.input_tokens=10;r.output_tokens=5;return r
class MeteredWriter(ScriptedWriter):
    def write(self,p):
        r=super().write(p);r.input_tokens=20;r.output_tokens=10;return r

def metered(a,role,s):return Metered() if role=='repair' else MeteredWriter()


def test_role_tokens_caps_spend_and_independent_writer_configuration():
    c=replace(preset('reasoning'),jobs=1,live=True)
    built=[]
    def factory(a,role,s):built.append((role,a));return metered(a,role,s)
    r=finish(c,agent_factory=factory)
    assert len(r.attempts)==2 and r.totals()['roles']['writer']=={'input':40,'output':20}
    assert [a for role,a in built if role=='writer']==[c.conditions[0].writer,c.conditions[1].writer]
    assert c.conditions[0].writer==c.conditions[1].writer and c.conditions[0].repair!=c.conditions[1].repair
    class Huge(Metered):
        def decide(self,c):r=super().decide(c);r.input_tokens=200;return r
    r=finish(replace(c,run_total_token_limit=128),agent_factory=lambda a,role,s:Huge())
    assert len(r.calls)==1 and r.attempts[0]['steps']==1 and r.totals()['input']==200
    assert r.state=='stopped' and not r.attempts[0]['certified']
    r=finish(replace(c,run_estimated_usd_limit=.000001),agent_factory=metered)
    assert len(r.calls)==1 and r.state=='stopped'
    job=replace(c.conditions[0],job_total_token_allowance=128)
    r=finish(replace(c,conditions=(job,)),agent_factory=lambda a,role,s:Huge())
    assert r.attempts[0]['status']=='unfinished' and len(r.calls)==1
    assert r.attempts[0]['memory_update_audit']['skipped']


def test_output_cap_and_writer_failure_preserve_certified_repair():
    class Truncated(Metered):
        def decide(self,c):return Reply(None,20,10,status='incomplete',end_reason='response output limit')
    c=EvaluationConfig(jobs=1,conditions=(Condition('one'),))
    r=finish(c,agent_factory=lambda *a:Truncated())
    assert not r.attempts[0]['certified'] and r.attempts[0]['reason']=='response output limit'
    class BrokenWriter:
        def write(self,p):raise ModelError('HTTP 502; unknown usage')
    c=replace(c,conditions=(Condition('one','structured'),))
    r=finish(c,agent_factory=lambda a,role,s:Metered() if role=='repair' else BrokenWriter())
    assert r.attempts[0]['certified'] and r.attempts[0]['status']=='success'
    assert r.attempts[0]['writer_error'] and r.totals()['unknown_calls']==1 and not r.totals()['usage_complete']
    assert r.state=='error'
    class Invalid(MeteredWriter):
        def write(self,p):return Reply(None,20,10,text='bad JSON')
    r=finish(c,agent_factory=lambda a,role,s:Metered() if role=='repair' else Invalid())
    assert r.attempts[0]['certified'] and r.attempts[0]['writer_error']
    assert r.totals()['roles']['writer']['input']==20 and r.totals()['usage_complete']
    assert r.attempts[0]['writer_output']['text']=='bad JSON'
    assert 'bad JSON' in render(r.report())


def test_config_rejection_presets_and_no_implicit_legacy_conversion():
    for name in ('reasoning','model','budget'):
        p=preset(name);assert len(p.conditions)==2 and p.conditions[0].writer==p.conditions[1].writer
    assert preset().attempts==24
    with pytest.raises(ValueError):replace(preset('model'),live=True,run_estimated_usd_limit=.1).validate()
    with pytest.raises(ValueError):replace(preset(),conditions=()).validate()
    with pytest.raises(ValueError):Condition('bad',repair=AgentConfig(reasoning='invented')).validate()
    with pytest.raises(ValueError):Condition('bad',writer=AgentConfig()).validate()
    with pytest.raises(ValueError):EvaluationConfig.from_dict({'schema_version':1,'mechanics':[]})


def test_adapter_passes_role_prompts_caps_and_records_incomplete_usage():
    repair=LiveAgent.__new__(LiveAgent);repair.settings=AgentConfig(reasoning='high',response_output_cap=512);repair.name='gpt-6-luna';repair.reasoning='high';repair.suite=suite()
    response=N(status='incomplete',incomplete_details=N(reason='max_output_tokens'),usage=N(input_tokens=17,output_tokens=512),output=[],output_text='',id='fake')
    repair.client=N(responses=N(create=Mock(return_value=response)))
    r=repair.decide({});args=repair.client.responses.create.call_args.kwargs
    assert r.action is None and r.end_reason=='response output limit' and r.output_tokens==512
    assert args['max_output_tokens']==512 and args['reasoning']=={'effort':'high'} and 'Repair reliably' in args['instructions']
    assert args['service_tier']=='default'
    repair.settings=replace(Condition('x').writer,response_output_cap=700)
    repair.write({});args=repair.client.responses.create.call_args.kwargs
    assert args['max_output_tokens']==700 and 'At job end' in args['instructions'] and 'tools' not in args


def test_pending_crash_recovery_and_storage_immutability(tmp_path):
    db=Store(tmp_path/'eval.sqlite3');snapshots=[]
    c=EvaluationConfig(jobs=1,live=True,conditions=(Condition('a'),))
    class InspectPending(Metered):
        def decide(self,context):
            snapshots.append(db.load(run.id))
            return super().decide(context)
    run=EvaluationRun(c,agent_factory=lambda *a:InspectPending(),on_checkpoint=db.checkpoint)
    db.begin(run);list(run.run())
    d=snapshots[1]
    assert d['state']=='interrupted' and d['attempts'][0]['steps']==1
    assert d['usage']['unknown_calls']==1 and not d['usage']['usage_complete']
    assert d['attempts'][0]['status']=='interrupted'
    assert d['attempts'][0]['usage']['unknown_calls']==1
    assert d['attempts'][0]['usage']['input']==10
    ref=db.save_config(c);v2=db.save_config(replace(c,name='Edited'),ref)
    assert v2['version']==2 and db.load_config(ref)==c
    with pytest.raises(ValueError):db.save_config(c,ref)
    before=deepcopy(db.load(run.id));run._manifest['config']['name']='Changed in memory'
    assert db.load(run.id)['manifest']['config']['name']==before['manifest']['config']['name']


def test_stop_during_request_retains_returned_usage_and_no_action(tmp_path):
    entered=threading.Event();release=threading.Event()
    class Waiting(Metered):
        def decide(self,c):entered.set();assert release.wait(5);return super().decide(c)
    ctl=Controller(Store(tmp_path/'db'),tmp_path/'out',agent_factory=lambda *a:Waiting())
    req=N(session_hash='wait');c=EvaluationConfig(jobs=1,conditions=(Condition('a'),))
    gen=ctl.start(json.dumps(c.to_dict()),False,req)
    try:
        next(gen);assert entered.wait(2);ctl.stop(req);release.set();last=list(gen)[-1]
        r=ctl.session(req)['run']
        assert r.state=='stopped' and r.totals()['input']==10 and r.totals()['usage_complete']
        assert r.attempts[0]['steps']==0 and not ctl.session(req)['busy']
    finally:release.set();gen.close()


def test_stop_during_pre_request_checkpoint_sends_nothing():
    class Never:
        def decide(self,c):raise AssertionError('must not send')
    r=EvaluationRun(EvaluationConfig(jobs=1,conditions=(Condition('a'),)),agent_factory=lambda *a:Never())
    def checkpoint(run):
        if run.calls and run.calls[-1]['status']=='pending':run.stop.set()
    r.checkpoint=checkpoint;list(r.run())
    assert r.calls[0]['status']=='not_sent' and r.totals()['known_calls']==0 and r.totals()['usage_complete']


def test_production_ui_lifecycle_exports_and_request_injection(tmp_path):
    import inspect,gradio as gr
    from gradio.helpers import special_args
    ctl=Controller(Store(tmp_path/'db'),tmp_path/'out')
    app=build_app(ctl);req=gr.Request(session_hash='production')
    for fn in app.fns.values():
        if fn.fn and 'request' in inspect.signature(fn.fn).parameters:
            args,*_=special_args(fn.fn,[None]*len(fn.inputs),request=req)
            assert inspect.signature(fn.fn).bind(*args).arguments['request'] is req
    c=replace(preset('reasoning'),jobs=1);text=json.dumps(c.to_dict())
    ref,_,_=ctl.save_config(text,None,False)
    restored,_,_=ctl.load_config(f'{ref["id"]}:{ref["version"]}')
    assert parse_config(restored)==c
    assert '2 conditions' in describe(c) and 'output cap' in describe(c)
    frames=list(ctl.start(restored,False,req));first=ctl.session(req)['run'];calls=len(first.calls)
    assert first.state=='completed' and len(first.attempts)==2
    assert frames[-1][3].value==first.id
    files=ctl.download(req);data=json.loads(__import__('pathlib').Path(files[1]).read_text())
    assert data['manifest']==first.manifest and data['usage']['estimated_usd']==0
    assert 'Raw events (ground truth)' in __import__('pathlib').Path(files[0]).read_text()
    list(ctl.replay(req));assert len(first.calls)==calls
    ctl.reset(req);assert ctl.session(req)['run'] is None
    list(ctl.start(text,False,req));assert ctl.session(req)['run'].id!=first.id
    ctl.load_run(first.id,req);assert ctl.session(req)['saved']['run_id']==first.id
    with pytest.raises(gr.Error):list(ctl.start(json.dumps(replace(c,live=True).to_dict()),False,req))


def parse_config(text):return EvaluationConfig.from_dict(json.loads(text))

@pytest.mark.parametrize('failure',[False,True])
def test_current_ui_export_failure_does_not_change_execution_error(tmp_path,monkeypatch,failure):
    import repair_shop.evaluation.app as app
    class Broken:
        def decide(self,c):raise ModelError('HTTP 502; usage unknown')
    ctl=Controller(Store(tmp_path/'db'),tmp_path/'out',agent_factory=(lambda *a:Broken()) if failure else None)
    monkeypatch.setattr(app,'export',lambda *a: (_ for _ in ()).throw(OSError('disk full')))
    req=N(session_hash='export');c=EvaluationConfig(jobs=1,conditions=(Condition('a'),))
    frames=list(ctl.start(json.dumps(c.to_dict()),False,req));r=ctl.session(req)['run']
    assert r.export_error and 'Report export failed' in frames[-1][1]
    if failure:assert r.error=='HTTP 502; usage unknown' and r.state=='error'
    else:assert not r.error and r.state=='completed' and r.attempts[0]['certified']
    assert ctl.store.load(r.id)['export_error']==r.export_error


def test_returned_final_test_can_certify_at_job_and_run_allowance_boundary():
    c=EvaluationConfig(jobs=1,conditions=(Condition('a','structured',job_total_token_allowance=128),))
    r=finish(c,agent_factory=metered)
    assert r.attempts[0]['certified'] and r.totals()['input']+r.totals()['output']==135
    assert not any(x['role']=='writer' for x in r.calls)
    assert r.attempts[0]['memory_update_audit']['skipped']
    r=finish(replace(c,run_total_token_limit=128),agent_factory=metered)
    assert r.state=='stopped' and r.attempts[0]['certified']


def test_writer_failure_trace_retains_prior_evidence():
    class FailSecond(ScriptedWriter):
        def __init__(self):self.n=0
        def write(self,p):
            self.n+=1
            if self.n==2:raise ModelError('writer request failed')
            return super().write(p)
    c=EvaluationConfig(jobs=2,conditions=(Condition('a','structured'),))
    r=finish(c,agent_factory=lambda a,role,s:ServiceDemo() if role=='repair' else FailSecond())
    assert r.attempts[1]['writer_error'] and r.attempts[1]['certified']
    assert r.attempts[1]['memory_after']==r.attempts[0]['memory_after']


def test_unreturned_or_invalid_usage_stays_unknown_and_none_store_empty():
    class InvalidUsage(ServiceDemo):
        def decide(self,c):return Reply({'name':'inspect','arguments':{}},None,5)
    r=finish(EvaluationConfig(jobs=1,conditions=(Condition('a'),)),agent_factory=lambda *a:InvalidUsage())
    assert r.totals()['unknown_calls']==1 and not r.totals()['usage_complete']
    assert r.attempts[0]['status']=='infrastructure_error'
    r=finish(EvaluationConfig(conditions=(Condition('a'),)))
    assert not r.memories[1,'a'].catalog and not r.memories[1,'a'].history


def test_correct_calibration_does_not_fix_physical_heat_and_log_status_is_literal():
    w=ServiceWorld(suite().jobs[3])
    assert w.gain==w.job.gain and w.bias==w.job.bias
    assert not w.call('test',{})['pass']
    for name,result in [('test',{'pass':False,'observation':'load certification did not pass'}),
                        ('operate',{'ok':False,'observation':'Service requires power off.'})]:
        log=observation('e',4,{'name':name,'arguments':{}},result)
        assert log['result']==result and 'false' in log['text']


def test_partial_rolling_boundary_is_visible_in_repair_context():
    seen=[]
    class Observed(ServiceDemo):
        def decide(self,c):seen.append(deepcopy(c));return super().decide(c)
    c=EvaluationConfig(jobs=2,conditions=(Condition('rolling','rolling',rolling_entry_limit=2),))
    r=finish(c,agent_factory=lambda *a:Observed())
    second=next(c for c in seen if c['ticket']['job']==2)
    assert second['partial_retained_jobs']==[1]
    assert second['prior_memory']==supplied(r.attempts[0]['observation_log'][-2:])


def test_export_retry_updates_saved_status_without_running_again(tmp_path,monkeypatch):
    import repair_shop.evaluation.app as app
    original=app.export
    ctl=Controller(Store(tmp_path/'db'),tmp_path/'out')
    req=N(session_hash='retry-export');c=EvaluationConfig(jobs=1,conditions=(Condition('a'),))
    monkeypatch.setattr(app,'export',lambda *a: (_ for _ in ()).throw(OSError('disk full')))
    list(ctl.start(json.dumps(c.to_dict()),False,req));run=ctl.session(req)['run']
    assert ctl.store.load(run.id)['export_error']
    calls=deepcopy(run.calls)
    monkeypatch.setattr(app,'export',original)
    files=ctl.download(req)
    assert len(files)==3 and run.calls==calls and run.state=='completed'
    assert not ctl.store.load(run.id)['export_error']
    assert not json.loads(__import__('pathlib').Path(files[1]).read_text())['export_error']


def test_recovery_of_pending_writer_preserves_pass_and_attempt_uncertainty(tmp_path):
    store=Store(tmp_path/'db');saved=[]
    class PendingWriter(ScriptedWriter):
        def write(self,p):saved.append(store.load(run.id));return super().write(p)
    run=EvaluationRun(EvaluationConfig(jobs=1,conditions=(Condition('a','structured'),)),
        agent_factory=lambda a,role,s:Metered() if role=='repair' else PendingWriter(),on_checkpoint=store.checkpoint)
    store.begin(run);list(run.run())
    d=saved[0];row=d['attempts'][0]
    assert d['state']=='interrupted' and row['status']=='success' and row['certified']
    assert row['usage']['unknown_calls']==d['usage']['unknown_calls']==1
    assert not row['usage']['usage_complete'] and row['usage']['input']==90


@pytest.mark.parametrize('guard',['tokens','usd'])
def test_conservative_admission_refuses_before_any_request(guard):
    class Never:
        def decide(self,c):raise AssertionError('Admission must prevent invocation')
    c=EvaluationConfig(jobs=1,live=True,conditions=(Condition('a'),),
        request_admission_policy='conservative-bytes-v1',
        run_total_token_limit=128 if guard=='tokens' else 1000000,
        run_estimated_usd_limit=1 if guard=='tokens' else .000001)
    r=finish(c,agent_factory=lambda *a:Never())
    assert r.state=='stopped' and not r.calls and r.attempts[0]['steps']==0
    assert 'admission guard' in r.stop_reason and r.events[-2]['kind']=='request_not_admitted'


def test_admission_records_reservations_and_stops_on_bound_violation():
    c=EvaluationConfig(jobs=1,live=True,conditions=(Condition('a','structured'),),request_admission_policy='conservative-bytes-v1')
    r=finish(c,agent_factory=metered)
    assert r.attempts[0]['certified'] and r.totals()['usage_complete']
    assert any(x['role']=='writer' for x in r.calls)
    assert all(x['input']<=x['reservation']['input_tokens'] and x['reservation']['output_tokens']==2048 for x in r.calls)
    old=c.to_dict();old.pop('request_admission_policy')
    assert EvaluationConfig.from_dict(old).request_admission_policy=='returned-usage-v1'
    class Violation(ServiceDemo):
        def decide(self,c):r=super().decide(c);r.output_tokens=2049;return r
    r=finish(c,agent_factory=lambda *a:Violation())
    assert len(r.calls)==1 and r.totals()['output']==2049 and 'exceeded' in r.stop_reason
