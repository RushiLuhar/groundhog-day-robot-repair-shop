from types import SimpleNamespace
from repair_shop.engine import Run
from repair_shop.model import DemoModel, Reply
from repair_shop.world import JOBS
from repair_shop.view import render
from repair_shop.app import start,reset,stop,replay,SESSIONS


def test_failure_render_is_not_success():
    class Bad(DemoModel):
        def decide(self,c): return Reply({'name':'inspect','arguments':{}})
    r=Run(Bad()); list(r.job('groundhog',JOBS[0]))
    view=render(r.events,r.results)
    assert 'UNFINISHED' in view and '12/12' in view and 'class="scene break"' in view
    assert 'Average steps per passing attempt' in view and '0/1' in view

def test_html_escapes_untrusted_model_notes():
    e={'sequence':1,'kind':'memory','mode':'structured','job':1,'ticket':{},'steps':1,'notes':'<script>bad()</script>'}
    assert '<script>' not in render([e])

def test_stop_reset_repeated_run_and_replay(monkeypatch):
    monkeypatch.setattr('repair_shop.app.time.sleep',lambda _:None)
    req=SimpleNamespace(session_hash='test-ui')
    first=list(start('Offline scripted demo',1,0.05,req))
    assert 'Shift complete' in first[-1][1]
    old=SESSIONS['test-ui']['run']; calls=len(old.calls)
    list(replay(0.05,req)); assert len(old.calls)==calls
    reset(req); assert SESSIONS['test-ui']['run'] is None
    gen=start('Offline scripted demo',3,0.05,req); next(gen); stop(req)
    assert list(gen)[-1][1]=='Stopped.'
    list(start('Offline scripted demo',1,0.05,req))
    assert SESSIONS['test-ui']['run'].id!=old.id
    assert len(SESSIONS['test-ui']['run'].results)==3


def test_ready_mode_changes_and_reset_preserve_recorded_results(monkeypatch):
    import gradio as gr
    from repair_shop.app import settings_changed, reset_described, get_session
    req=SimpleNamespace(session_hash='selected-mode-regression')
    monkeypatch.setattr('repair_shop.app.OpenAIModel',lambda: (_ for _ in ()).throw(AssertionError('selection must not create a client')))
    html,status,description=settings_changed('Live OpenAI (paid)',2,req)
    assert 'OpenAI selected (paid)' in status and 'OPENAI SELECTED' in html
    assert '2 jobs × 3 bays = 6' in description
    assert 'Ready · OpenAI selected (paid)' in settings_changed('Live OpenAI (paid)',10,req)[1]
    assert 'free demo selected' in settings_changed('Offline scripted demo',2,req)[1]
    session=get_session(req); session['busy']=True
    assert settings_changed('Live OpenAI (paid)',2,req)==(gr.skip(),gr.skip(),gr.skip())
    session['busy']=False
    run=Run(DemoModel()); list(run.run(JOBS[:1])); session['run']=run
    html,status,description=settings_changed('Live OpenAI (paid)',2,req)
    assert html==gr.skip() and status==gr.skip() and 'Completed shift' in description
    assert 'Free demo' in description
    html,status,_=reset_described('Live OpenAI (paid)',2,req)
    assert 'OpenAI selected (paid)' in status and 'OPENAI SELECTED' in html
    assert session['run'] is None


def test_full_ticket_set_allowed_through_live_ui_with_mock_client(monkeypatch):
    # Exercise the paid-mode path without constructing an OpenAI client or making API calls.
    monkeypatch.setattr('repair_shop.app.OpenAIModel',DemoModel)
    monkeypatch.setattr('repair_shop.app.time.sleep',lambda _:None)
    req=SimpleNamespace(session_hash='full-ticket-set')
    final=list(start('Live OpenAI (paid)',10,.05,req))[-1]
    run=SESSIONS[req.session_hash]['run']
    assert run.completed and len(run.results)==30
    assert {(r['mode'],r['job']) for r in run.results}=={(m,j.number) for m in ('groundhog','notebook','structured') for j in JOBS}
    assert all(r['steps']<=12 for r in run.results)
    assert 'Shift complete' in final[1]


def test_ticket_bounds_rejected_before_client_creation(monkeypatch):
    monkeypatch.setattr('repair_shop.app.OpenAIModel',lambda: (_ for _ in ()).throw(AssertionError('invalid count must not create a client')))
    for count in (0,11):
        req=SimpleNamespace(session_hash=f'invalid-count-{count}')
        result=list(start('Live OpenAI (paid)',count,.05,req))
        assert result[-1][1]=='Choose between 1 and 10 jobs per bay.'
        assert SESSIONS[req.session_hash]['run'] is None
