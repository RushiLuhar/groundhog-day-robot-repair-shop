"""Exercise production callbacks with temporary storage and fake model requests."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import json
import threading
import pytest
from repair_shop import experiments_ui as ui, experiment as cli, reports
from repair_shop.app import SESSIONS, stop
from repair_shop.config import ExperimentConfig
from repair_shop.engine import Run
from repair_shop.model import DemoModel, Reply, ModelError
from repair_shop.storage import ExperimentStore
from repair_shop.view import configuration_description


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    db=ExperimentStore(tmp_path/'runs.sqlite3')
    monkeypatch.setattr(ui,'store',lambda:db)
    original=reports.export
    monkeypatch.setattr(ui,'export',lambda run:original(run,tmp_path/'exports'))
    monkeypatch.setattr(cli,'export',lambda run:original(run,tmp_path/'exports'))
    request=SimpleNamespace(session_hash=f'recovery-{tmp_path.name}')
    yield db,request
    SESSIONS.pop(request.session_hash,None)


def fake_factory(monkeypatch,model):
    monkeypatch.setattr(ui,'Run',lambda **kw:Run(model=model,**kw))


class Metered(DemoModel):
    name='gpt-6-luna';live=True
    def decide(self,c):
        r=super().decide(c);r.input_tokens=7;r.output_tokens=3;return r


def test_pending_checkpoint_recovers_attempt_without_mutating_history(sandbox):
    db,_=sandbox
    snapshots=[]
    class Observe(Metered):
        def decide(self,c):
            if c['current_job_exchanges']:
                snapshots.append(db.load_run(run.id))
            return super().decide(c)
    run=Run(model=Observe(),experiment=ExperimentConfig(jobs_per_bay=1,live=True))
    db.begin_run(run);run.on_checkpoint=lambda r:db.checkpoint(r)
    list(run.run())
    row=snapshots[0];original=deepcopy(row['report'])
    assert row['status']=='running' and row['report']['active_request']['status']=='pending'
    assert not row['report']['usage_complete']
    saved=ui.SavedRun(row['report'],row['status'])
    data=saved.report();result=data['results'][0]
    assert result['interrupted'] and result['steps']==1 and not result['passed']
    assert result['input']+result['output']==10
    assert len(data['results'])==1 and data['usage']['input']+data['usage']['output']==10
    assert reports.run_state(saved)=='interrupted' and not data['usage_complete']
    assert row['report']==original
    html=ui.show_run(saved,state=reports.run_state(saved))
    assert '2 not attempted' in html and 'Usage may be incomplete' in html
    assert 'SHIFT INTERRUPTED' in html
    # Legacy recovery uses recorded events, conservatively retaining only known steps.
    legacy=deepcopy(original)
    for k in ('active_request','active_attempt','interrupted'):legacy.pop(k,None)
    legacy['usage_complete']=True
    recovered=ui.SavedRun(legacy,'running')
    assert len(recovered.results)==1 and recovered.results[0]['steps']==1
    assert not recovered.usage_complete


def test_cli_interrupt_counts_active_attempt_and_unknown_request(sandbox,monkeypatch):
    db,_=sandbox
    class Interrupt(Metered):
        def decide(self,c):
            if c['current_job_exchanges']:raise KeyboardInterrupt()
            return super().decide(c)
    monkeypatch.setattr(cli,'Run',lambda **kw:Run(model=Interrupt(),**kw))
    r=cli.run_config(ExperimentConfig(jobs_per_bay=1,live=True),db=db)
    assert r.interrupted and not r.usage_complete and r.error is None
    assert len(r.results)==1 and r.results[0]['steps']==1 and r.results[0]['interrupted']
    assert r.results[0]['input']+r.results[0]['output']==10
    row=db.load_run(r.id)
    assert row['status']=='stopped' and not row['report']['usage_complete']


@pytest.mark.parametrize('api_error',[False,True])
def test_production_callback_export_failure_preserves_execution(sandbox,monkeypatch,api_error):
    db,request=sandbox
    class Fail(Metered):
        def decide(self,c):raise ModelError('HTTP 502; request usage unknown')
    if api_error:fake_factory(monkeypatch,Fail())
    monkeypatch.setattr(ui,'export',lambda r: (_ for _ in ()).throw(OSError('disk full')))
    final=list(ui.execute(ExperimentConfig(jobs_per_bay=1),None,0,request))[-1]
    r=SESSIONS[request.session_hash]['run'];row=db.load_run(r.id)
    assert 'Report export failed' in final[0] and 'Report export failed' in final[1]
    assert row['report']['export_error']==r.export_error
    assert not SESSIONS[request.session_hash]['busy']
    if api_error:
        assert r.error=='HTTP 502; request usage unknown' and row['report']['error']==r.error
        assert 'HTTP 502' in final[1] and row['status']=='error'
        assert 'SHIFT STOPPED · ERROR' in final[0]
    else:
        assert r.completed and r.error is None and row['status']=='completed'
        assert 'SHIFT COMPLETE' in final[0] and 'SHIFT STOPPED · ERROR' not in final[0]
        assert 'Run complete.' in final[1]


def test_production_persistence_failure_is_distinct(sandbox,monkeypatch):
    db,request=sandbox
    real=db.checkpoint
    def checkpoint(run,final=False):
        if final:raise OSError('unavailable storage')
        real(run,final)
    monkeypatch.setattr(db,'checkpoint',checkpoint)
    final=list(ui.execute(ExperimentConfig(jobs_per_bay=1),None,0,request))[-1]
    r=SESSIONS[request.session_hash]['run']
    assert r.completed and r.error is None and r.persistence_error
    assert 'Results and exact settings are saved locally.' not in final[1]
    assert 'Saving the run checkpoint failed' in final[0]


def test_production_local_error_recovers_once(sandbox,monkeypatch):
    db,request=sandbox
    class LocalFailure(Metered):
        def decide(self,c):
            if c['current_job_exchanges']:raise RuntimeError('local error')
            return super().decide(c)
    fake_factory(monkeypatch,LocalFailure())
    list(ui.execute(ExperimentConfig(jobs_per_bay=1,live=True),None,0,request))
    r=SESSIONS[request.session_hash]['run']
    assert len(r.results)==1 and r.results[0]['steps']==1
    assert not r.usage_complete and r.results[0]['interrupted']
    assert db.load_run(r.id)['status']=='error'


def test_production_stop_waits_for_returned_usage(sandbox,monkeypatch):
    db,request=sandbox
    entered=threading.Event();release=threading.Event()
    class Waiting(Metered):
        def decide(self,c):
            entered.set();assert release.wait(5)
            return super().decide(c)
    fake_factory(monkeypatch,Waiting())
    gen=ui.execute(ExperimentConfig(jobs_per_bay=1,live=True),None,0,request)
    try:
        next(gen);assert entered.wait(2)
        stop(request);release.set();final=list(gen)[-1]
        r=SESSIONS[request.session_hash]['run']
        assert r.usage_complete and len(r.calls)==1 and len(r.results)==1
        assert r.results[0]['steps']==0 and r.totals()['input']+r.totals()['output']==10
        assert db.load_run(r.id)['status']=='stopped' and not SESSIONS[request.session_hash]['busy']
        assert 'SHIFT STOPPED' in final[0]
    finally:release.set();gen.close()


def test_current_callbacks_settings_saved_load_reset_replay(sandbox,monkeypatch):
    db,request=sandbox
    app=ui.build_app()
    callbacks={f.fn.__name__:f.fn for f in app.fns.values() if f.fn}
    c=ExperimentConfig(task_set='learning-v1',jobs_per_bay=5)
    values=ui.experiment_values(c)
    selected=callbacks['select_all'](c.to_dict(),*values,request)
    chosen=ExperimentConfig.from_dict(selected[1])
    assert chosen.jobs_per_bay==32 and '32 of 32' in selected[-1]
    assert '5 of 32' in ui.selection_description(c.task_set,5)
    # Apply a mechanic's output caps, save, then restore exact values.
    m=c.mechanics[2]
    draft,_=callbacks['apply_mechanic'](c.to_dict(),m.bay_id,m.name,m.model,m.reasoning,m.memory,
        m.notebook_exchanges,m.memory_tokens,m.step_limit,2048,3072,m.annotation,m.memory_update_policy)
    saved=callbacks['save_config'](draft,None,*values)
    ref=saved[1]
    loaded=callbacks['load_config'](f"{ref['id']}:{ref['version']}",'structured')
    restored=ExperimentConfig.from_dict(loaded[0])
    assert restored.mechanics[2].repair_output_tokens==2048 and restored.mechanics[2].memory_output_tokens==3072
    assert '2048 / 3072' in configuration_description(restored)
    assert '1024 / 1600' in configuration_description(restored)
    # Production start, replay, reset, repeated run, and saved-run loading.
    small=replace(restored,jobs_per_bay=1)
    list(callbacks['start'](small.to_dict(),None,0,*ui.experiment_values(small),request))
    first=SESSIONS[request.session_hash]['run'];count=len(first.calls)
    list(callbacks['replay'](0,request));assert len(first.calls)==count
    callbacks['reset'](small.to_dict(),*ui.experiment_values(small),request)
    assert SESSIONS[request.session_hash]['run'] is None
    list(callbacks['start'](small.to_dict(),None,0,*ui.experiment_values(small),request))
    assert SESSIONS[request.session_hash]['run'].id!=first.id
    callbacks['view_saved'](first.id,request)
    assert SESSIONS[request.session_hash]['run'].id==first.id
    assert db.load_config(ref['id'],ref['version']).jobs_per_bay==5


def test_export_retry_clears_only_export_warning(sandbox,tmp_path):
    _,request=sandbox
    list(ui.execute(ExperimentConfig(jobs_per_bay=1),None,0,request))
    r=SESSIONS[request.session_hash]['run']
    r.export_error='Old export failure'
    r.error='Original execution error'
    paths=reports.export(r,tmp_path/'retry')
    assert not r.export_error and r.error=='Original execution error'
    assert json.loads(__import__('pathlib').Path(paths[1]).read_text())['export_error']==''


@pytest.mark.parametrize('kind',['repair','memory'])
def test_stop_during_pending_checkpoint_makes_no_new_request(kind):
    class NeverCalled(Metered):
        def decide(self,c):
            if kind=='repair':raise AssertionError('request started after stop')
            return super().decide(c)
        def maintain(self,p):raise AssertionError('memory request started after stop')
    r=Run(model=NeverCalled(),experiment=ExperimentConfig(jobs_per_bay=1,live=True))
    def checkpoint(run):
        if run.active_request and run.active_request['kind']==kind:run.stop.set()
    r.on_checkpoint=checkpoint
    list(r.run())
    assert r.usage_complete and r.active_request is None
    assert not any(c['kind']==kind for c in r.calls)


def test_recovery_preserves_pass_before_interrupted_maintenance(sandbox):
    db,_=sandbox
    snapshots=[]
    class Observe(Metered):
        def maintain(self,p):
            snapshots.append(db.load_run(r.id)['report'])
            return super().maintain(p)
    r=Run(model=Observe(),experiment=ExperimentConfig(jobs_per_bay=1,live=True))
    db.begin_run(r);r.on_checkpoint=lambda run:db.checkpoint(run)
    list(r.run())
    saved=ui.SavedRun(snapshots[0],'running')
    assert len(saved.results)==3 and all(x['passed'] for x in saved.results)
    assert saved.results[-1]['interrupted'] and saved.results[-1]['warning']
    assert not saved.usage_complete
    assert saved.data['active_request']['kind']=='memory'
    assert saved.results[-1]['steps']==r.results[-1]['steps']
