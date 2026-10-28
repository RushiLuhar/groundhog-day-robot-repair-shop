import json
import threading
from types import SimpleNamespace
import pytest
from repair_shop.costs import estimate, total_cost
from repair_shop.engine import Run
from repair_shop.model import DemoModel, Reply
from repair_shop.world import JOBS
from repair_shop.reports import export, summary
from repair_shop.view import render
from repair_shop.app import start, SESSIONS, stop


def test_rates_unknown_offline_and_long_context():
    assert estimate('gpt-6-luna',1000,200)==pytest.approx(.0002)
    assert estimate('unknown',1000,200) is None
    assert estimate('unknown',1000,200,False)==0
    assert estimate('gpt-6-luna',300000,1000)==pytest.approx(.06075)
    assert total_cost([{'cost_usd':.1},{'cost_usd':None}]) is None


def test_memory_costs_and_safe_portable_exports(tmp_path):
    class Metered(DemoModel):
        name='gpt-6-luna'; live=True
        private_key='DO-NOT-EXPORT-THIS-CANARY'
        def decide(self,c):
            reply=super().decide(c); reply.input_tokens=100; reply.output_tokens=10
            return reply
        def maintain(self,c):
            reply=super().maintain(c); reply.input_tokens=200; reply.output_tokens=20
            return reply
    run=Run(Metered()); list(run.run(JOBS[:1]))
    assert run.completed and run.selected_jobs==1
    assert run.totals('structured')['maintenance']==220
    assert run.totals()['cost_usd']==pytest.approx(sum(estimate(run.model.name,c['input'],c['output']) for c in run.calls))
    files=export(run,tmp_path)
    for path in files:
        text=__import__('pathlib').Path(path).read_text()
        assert 'DO-NOT-EXPORT-THIS-CANARY' not in text
        assert str(tmp_path) not in text
    data=json.loads(__import__('pathlib').Path(files[1]).read_text())
    assert data['state']=='completed' and data['configuration']['model']=='gpt-6-luna'
    assert 'events' not in data and 'calls' not in data  # no raw response identifiers
    html=__import__('pathlib').Path(files[0]).read_text()
    assert 'SHIFT COMPLETE' in html and '3/3' in html and 'clocked-out' in html


def test_waiting_and_maintenance_override_previous_tool_animation():
    run=Run(DemoModel()); list(run.run(JOBS[:1]))
    idx=next(i for i,e in enumerate(run.events) if e['kind']=='maintenance_start')
    view=render(run.events[:idx+1],running=True,selected_jobs=1)
    assert 'class="scene saving"' in view and 'SAVING MEMORY' in view
    idx=next(i for i,e in enumerate(run.events) if e['kind']=='thinking' and e['steps']>0)
    view=render(run.events[:idx+1],running=True,selected_jobs=1,elapsed=5)
    assert 'class="scene thinking"' in view and '5s since last event' in view


def test_rejected_or_stopped_runs_never_claim_schedule_completed():
    run=Run(DemoModel()); run.selected_jobs=3; list(run.job('groundhog',JOBS[0]))
    assert summary(run)['state']=='stopped'
    view=render(run.events,run.results,selected_jobs=3,state='stopped')
    assert 'SHIFT STOPPED' in view and '8 not attempted' in view
    run.error='Model rejected request'
    assert summary(run)['usage_complete'] is False
    assert summary(run)['state']=='error'


def test_thinking_event_visible_while_model_blocked_and_stop_accounts_return(monkeypatch):
    entered=threading.Event(); release=threading.Event()
    class Waiting(DemoModel):
        def decide(self,c):
            entered.set()
            assert release.wait(5)
            return Reply({'name':'inspect','arguments':{}},input_tokens=7,output_tokens=3)
    monkeypatch.setattr('repair_shop.app.DemoModel',Waiting)
    monkeypatch.setattr('repair_shop.app.time.sleep',lambda _:None)
    req=SimpleNamespace(session_hash='blocked-model-test')
    gen=start('Offline scripted demo',1,.05,req); next(gen)
    try:
        frames=[]
        while not any('Choosing the next action' in html for html,_ in frames):
            frames.append(next(gen))
        assert entered.wait(2)
        stop(req); release.set()
        final=list(gen)[-1]
        run=SESSIONS[req.session_hash]['run']
        assert final[1]=='Stopped.' and len(run.calls)==1
        assert run.totals()['input']==7 and run.totals()['output']==3
        assert not any(e['kind']=='action' for e in run.events)
    finally:
        release.set(); gen.close()


def test_quips_are_robot_speech_bubbles():
    html=render(selected_jobs=3)
    assert html.count('aria-label="Mechanic says"')==3
    assert html.index('aria-label="Mechanic says"') < html.index('class="scene idle"')


def test_stop_at_memory_start_does_not_launch_memory_call():
    class NoMemoryCall(DemoModel):
        def maintain(self,c): raise AssertionError('must not make a new memory call after stop')
    run=Run(NoMemoryCall())
    run.on_event=lambda e: run.stop.set() if e['kind']=='maintenance_start' else None
    list(run.job('structured',JOBS[0]))
    assert run.results[0]['warning']=='Memory write skipped after stop.'
    assert all(c['kind']!='memory' for c in run.calls)
