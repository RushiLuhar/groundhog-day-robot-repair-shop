"""Local-only Gradio workshop. Explicit live opt-in; offline mode is the default."""
import os
os.environ['GRADIO_ANALYTICS_ENABLED']='False'
import threading
import time
import gradio as gr
from .engine import Run
from .model import DemoModel, OpenAIModel, ModelError
from .world import JOBS
from .view import CSS, render

SESSIONS = {}
LOCK = threading.Lock()

def get_session(request):
    key=request.session_hash
    with LOCK:
        return SESSIONS.setdefault(key,{'stop':threading.Event(),'run':None,'busy':False})

def start(kind, count, speed, request: gr.Request):
    session=get_session(request)
    with LOCK:
        if session['busy']:
            raise gr.Error('A shift is already active. Stop it before starting another.')
        session['busy']=True
        session['stop']=threading.Event()
    live=kind=='Live OpenAI (paid)'
    try:
        count=int(count)
        if live and count>4:
            raise ModelError('Live shifts are limited to 4 jobs per bay (12 jobs total).')
        model=OpenAIModel() if live else DemoModel()
        run=Run(model,session['stop']); session['run']=run
        yield render(live=live,model=model.name,running=True), 'Shift started. Stop takes effect after any in-flight API request returns.'
        shown=[]; offset=0
        for _ in run.run(JOBS[:count]):
            pending=run.events[offset:]; offset=len(run.events)
            for event in pending:
                shown.append(event)
                yield render(shown,run.results,live,model.name,True,run.error), f'{len(run.results)} jobs settled · {len(run.calls)} calls · {run.totals()["input"]+run.totals()["output"]:,} tokens'
                if not session['stop'].is_set(): time.sleep(float(speed))
        yield render(run.events,run.results,live,model.name,False,run.error), 'Stopped.' if session['stop'].is_set() else 'Shift complete. Replay makes no model calls. Start another shift to reset all memory.'
    except ModelError as exc:
        yield render(error=str(exc)), str(exc)
    finally:
        with LOCK: session['busy']=False

def stop(request: gr.Request):
    get_session(request)['stop'].set()
    return 'Stop requested. An in-flight request is allowed to settle so usage can be recorded; no new calls follow.'

def reset(request: gr.Request):
    session=get_session(request)
    if session['busy']:
        session['stop'].set()
        raise gr.Error('Stopping the active shift. Reset once it has settled.')
    session['run']=None
    return render(), 'Fresh shift. All prior memory cleared.'

def replay(speed, request: gr.Request):
    session=get_session(request)
    with LOCK:
        if session['busy']: raise gr.Error('Wait for the active shift to settle.')
        run=session['run']
        if run is None: raise gr.Error('Run a shift first.')
        session['busy']=True; session['stop']=threading.Event()
    try:
        shown=[]
        for event in run.events:
            if session['stop'].is_set(): break
            shown.append(event)
            settled={(e['mode'],e['job']) for e in shown if e['kind']=='invoice'}
            rs=[r for r in run.results if (r['mode'],r['job']) in settled]
            yield render(shown,rs,run.model.live,run.model.name,True), 'Replaying recorded events · no API calls'
            time.sleep(float(speed))
        yield render(run.events,run.results,run.model.live,run.model.name,False,run.error), 'Replay ended · no API calls'
    finally:
        with LOCK: session['busy']=False

def build_app():
    with gr.Blocks(title='Groundhog Day • Robot Repair Shop',analytics_enabled=False) as app:
        gr.Markdown('### Workshop controls\nOffline rehearsal is free. Live mode uses your server-side configured OpenAI model and key. One shift uses identical jobs in all three bays.')
        with gr.Row():
            kind=gr.Radio(['Offline scripted demo','Live OpenAI (paid)'],value='Offline scripted demo',label='Engine')
            count=gr.Slider(1,10,value=3,step=1,label='First N jobs per bay · live maximum 4')
            speed=gr.Slider(0.05,0.8,value=0.15,step=0.05,label='Replay / animation beat (seconds)')
        with gr.Row():
            go=gr.Button('Start shift',variant='primary'); halt=gr.Button('Stop'); again=gr.Button('Replay last shift'); clear=gr.Button('Reset workshop')
        status=gr.Textbox(value='Ready · offline mode · no API calls',label='Shift status',interactive=False)
        workshop=gr.HTML(render())
        go.click(start,[kind,count,speed],[workshop,status],concurrency_limit=1,api_visibility='private')
        halt.click(stop,[],status,queue=False,api_visibility='private')
        clear.click(reset,[],[workshop,status],queue=False,api_visibility='private')
        again.click(replay,[speed],[workshop,status],concurrency_limit=1,api_visibility='private')
    return app

if __name__=='__main__':
    build_app().queue(max_size=8).launch(server_name='127.0.0.1',server_port=7860,share=False,
        css=CSS,theme=gr.themes.Base(primary_hue='lime',neutral_hue='slate'),show_error=False,
        blocked_paths=[str(__import__('pathlib').Path(__file__).resolve().parents[1]/'.env')])
