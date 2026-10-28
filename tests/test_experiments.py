from copy import deepcopy
from dataclasses import replace
import json
import pytest
from repair_shop.config import ExperimentConfig, MechanicConfig, default_mechanics
from repair_shop.engine import Run
from repair_shop.model import DemoModel, Reply
from repair_shop.storage import ExperimentStore
from repair_shop.tasks import SUITES, get_suite
from repair_shop.tasks.diagnostic import DiagnosticWorld,JOBS
from repair_shop.experiments_ui import SavedRun
from repair_shop.reports import export


def finish(config,**kw):
    r=Run(experiment=config,**kw)
    list(r.run())
    return r


@pytest.mark.parametrize('suite',list(SUITES))
def test_entire_suite_solvable_from_observations(suite):
    r=finish(ExperimentConfig(task_set=suite,jobs_per_bay=10))
    assert r.completed and len(r.results)==30
    assert all(x['passed'] and x['steps']<=12 for x in r.results)
    assert not r.error and r.totals()['input']==0
    assert all(not x['warning'] for x in r.results)


def test_targeted_diagnostics_and_constraints():
    w=DiagnosticWorld(JOBS[0]);r=w.call('inspect',{})
    assert not {'faults','recipe','next_action','title'} & r.keys()
    assert 'cooler' not in json.dumps(r)
    wrong=w.call('operate',{'operation':'tune'})
    assert not wrong['ok'] and 'vent' not in json.dumps(wrong)
    assert w.call('diagnose',{'component':'cooler'})['tuning_interlock']=='pressure prevents adjustment'
    assert not w.call('operate',{'operation':'replace_fuse'})['ok']
    w.call('operate',{'operation':'power_off'})
    assert w.call('operate',{'operation':'replace_fuse'})['ok']
    assert not w.call('operate',{'operation':'replace_fuse'})['ok']
    assert not w.call('test',{})['pass']
    revised=DiagnosticWorld(JOBS[8])
    assert revised.call('diagnose',{'component':'cooler'})['release_valve']=='locked'
    assert not revised.call('operate',{'operation':'vent'})['ok']


def test_configuration_validation_and_round_trip():
    c=ExperimentConfig(); assert ExperimentConfig.from_dict(c.to_dict())==c
    for changes in ({'repetitions':0},{'jobs_per_bay':11},{'live':'yes'},{'task_set':'uploaded-code'}):
        with pytest.raises(ValueError):replace(c,**changes).validate()
    with pytest.raises(ValueError):replace(c.mechanics[0],model='gpt-6-astra',reasoning='none').validate()
    unknown=c.to_dict();unknown['OPENAI_API_KEY']='not-a-secret'
    with pytest.raises(ValueError):ExperimentConfig.from_dict(unknown)


def test_memory_policy_independent_of_bay_and_repetitions_reset():
    mechanics=tuple(replace(m,memory='notebook',notebook_exchanges=2) for m in default_mechanics())
    r=finish(ExperimentConfig(jobs_per_bay=2,repetitions=2,mechanics=mechanics))
    assert len(r.results)==12
    starts=[e for e in r.events if e['kind']=='start']
    assert all(e['prior']==[] for e in starts if e['job']==1)
    assert all(len(e['prior'])==2 for e in starts if e['job']==2)
    zero=replace(mechanics[0],notebook_exchanges=0)
    r=finish(ExperimentConfig(jobs_per_bay=2,mechanics=(zero,*mechanics[1:])))
    assert all(e['prior']==[] for e in r.events if e['kind']=='start' and e['mode']==zero.bay_id)


def test_per_bay_caps_and_known_usage_budget():
    c=ExperimentConfig(jobs_per_bay=1,mechanics=tuple(replace(m,step_limit=i+1) for i,m in enumerate(default_mechanics())))
    r=finish(c)
    assert [x['steps'] for x in r.results]==[1,2,3]
    class Counted(DemoModel):
        live=True;name='gpt-6-luna'
        def decide(self,c):return Reply({'name':'inspect','arguments':{}},900,200)
    c=ExperimentConfig(jobs_per_bay=2,max_total_tokens=1000,live=True)
    r=finish(c,model_factory=lambda _:Counted())
    assert len(r.calls)==1 and r.totals()['input']==900
    assert not r.completed and r.stop_reason and len(r.results)==1


def test_versioned_store_immutable_snapshots_and_read_only_history(tmp_path):
    db=ExperimentStore(tmp_path/'test.sqlite3');c=ExperimentConfig(jobs_per_bay=1)
    ref=db.save_config(c);v2=db.save_config(replace(c,name='Edited'),ref['id'],1)
    assert v2['version']==2 and db.load_config(ref['id'],1).name==c.name
    with pytest.raises(ValueError):db.save_config(c,ref['id'],1)
    r=Run(experiment=c);r.selected_jobs=1;r.config_reference=ref
    db.begin_run(r,ref);r.on_checkpoint=lambda r:db.checkpoint(r)
    list(r.run());db.checkpoint(r,True)
    row=ExperimentStore(db.path).load_run(r.id)
    assert row['config_snapshot']==json.loads(json.dumps(c.to_dict()))
    assert row['config_version']==1 and row['status']=='completed'
    saved=SavedRun(row['report'])
    assert saved.report()==r.report()
    files=export(saved,tmp_path/'exports')
    data=json.loads(open(files[1]).read())
    assert data['task_fingerprint']==r.suite.fingerprint and data['configuration']==row['config_snapshot']
    r.events.clear();assert row['report']['events']


def test_independent_models_receive_config_and_memory_calls_count():
    built=[]
    class Counted(DemoModel):
        live=True;name='gpt-6-luna'
        def decide(self,c):
            r=super().decide(c);r.input_tokens=10;r.output_tokens=2;return r
        def maintain(self,p):
            r=super().maintain(p);r.input_tokens=20;r.output_tokens=3;return r
    def factory(m):built.append(m);return Counted()
    c=ExperimentConfig(jobs_per_bay=1,live=True)
    r=finish(c,model_factory=factory)
    assert built==list(c.mechanics)
    assert r.totals()['maintenance']==23
    assert sum(x['input']+x['output'] for x in r.calls)==r.totals()['input']+r.totals()['output']
    assert len({id(m) for m in r.models.values()})==3


def test_gradio_callbacks_accept_injected_request(tmp_path,monkeypatch):
    import inspect
    import gradio as gr
    from gradio.helpers import special_args
    from repair_shop import experiments_ui
    monkeypatch.setattr(experiments_ui,'store',lambda:ExperimentStore(tmp_path/'ui.sqlite3'))
    app=experiments_ui.build_app()
    request=gr.Request(session_hash='callback-test')
    tested=[]
    for block_fn in app.fns.values():
        fn=block_fn.fn
        if fn is None or 'request' not in inspect.signature(fn).parameters:continue
        args,*_=special_args(fn,[None]*len(block_fn.inputs),request=request)
        bound=inspect.signature(fn).bind(*args)
        assert bound.arguments['request'] is request
        tested.append(fn.__name__)
    assert {'start','changed','reset','replay','view_saved'}<=set(tested)
