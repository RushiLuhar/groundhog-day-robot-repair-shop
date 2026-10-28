"""Local-only Gradio workshop. Explicit live opt-in; offline mode is the default."""
import os
os.environ['GRADIO_ANALYTICS_ENABLED']='False'
import threading
import time
import queue
from copy import deepcopy
from .reports import export, run_state
import gradio as gr
from .engine import Run
from .model import DemoModel, OpenAIModel, ModelError
from .world import JOBS
from .view import CSS, render, experiment_description

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
        messages=queue.Queue()
        run=Run(model,session['stop']); session['run']=run
        run.selected_jobs=count
        abandoned=threading.Event()
        def on_event(event):
            # Snapshot only public simulation data. No prompts, keys or client objects in logs.
            print(f"run={run.id[:8]} bay={event['mode']} job={event['job']} step={event['steps']} event={event['kind']}",flush=True)
            messages.put((event,deepcopy(run.results),deepcopy(run.calls)))
            if not live and not run.stop.is_set(): time.sleep(float(speed))
        run.on_event=on_event
        def work():
            try:
                for _ in run.run(JOBS[:count]): pass
            except Exception:
                run.error='Unexpected local execution error. Shift stopped; usage may be incomplete.'
                run.stop.set()
            finally:
                messages.put(None)
                with LOCK:
                    if abandoned.is_set(): session['busy']=False
        yield render(live=live,model=model.name,running=True,selected_jobs=count), 'Shift started. Stop takes effect after any in-flight API request returns.'
        worker=threading.Thread(target=work,daemon=True); worker.start()
        shown=[]; rs=[]; calls=[]; last_event=time.monotonic()
        try:
            while True:
                try: message=messages.get(timeout=1)
                except queue.Empty:
                    elapsed=int(time.monotonic()-last_event)
                    yield render(shown,rs,live,model.name,True,selected_jobs=count,elapsed=elapsed,calls=calls), f'Shift active · {len(rs)}/{count*3} attempts settled · waiting {elapsed}s since last event. Stop will settle the in-flight request.'
                    continue
                if message is None: break
                event,rs,calls=message; shown.append(event); last_event=time.monotonic()
                yield render(shown,rs,live,model.name,True,selected_jobs=count,calls=calls), f"{event['kind']} · {event['mode']} · job {event['job']} · {len(rs)}/{count*3} attempts settled"
            # Persist safe exports locally so a browser refresh does not erase the only copy.
            export(run)
            status='Shift ended with an error. Known usage recorded; review the error below.' if run.error else 'Stopped.' if not run.completed else 'Shift complete. All scheduled attempts settled. Download the report or replay without model calls.'
            yield render(run.events,run.results,live,model.name,error=run.error,selected_jobs=count,state=run_state(run),calls=run.calls), status
        finally:
            with LOCK:
                abandoned.set()
                if worker.is_alive(): run.stop.set()
    except ModelError as exc:
        yield render(error=str(exc)), str(exc)
    finally:
        with LOCK:
            if 'worker' not in locals() or not worker.is_alive(): session['busy']=False

def stop(request: gr.Request):
    get_session(request)['stop'].set()
    return 'Stop requested. An in-flight request is allowed to settle so usage can be recorded; no new calls follow.'

def reset(request: gr.Request):
    session=get_session(request)
    if session['busy']:
        session['stop'].set()
        raise gr.Error('Stopping the active shift. Reset once it has settled.')
    session['run']=None
    return render(selected_jobs=3), 'Fresh shift. All prior memory cleared.'

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
            yield render(shown,rs,run.model.live,run.model.name,True,selected_jobs=run.selected_jobs,state='replay'), 'Replaying recorded events · no API calls'
            time.sleep(float(speed))
        yield render(run.events,run.results,run.model.live,run.model.name,False,run.error,selected_jobs=run.selected_jobs,state=run_state(run),calls=run.calls), 'Replay ended · no API calls'
    finally:
        with LOCK: session['busy']=False

def download_results(request: gr.Request):
    session=get_session(request)
    if session['busy']: raise gr.Error('Wait for the shift to settle before exporting results.')
    if session['run'] is None: raise gr.Error('Run a shift first.')
    return export(session['run'])

def describe_experiment(kind, count, request: gr.Request):
    session=get_session(request)
    run=session['run']
    if run is not None:
        phase='running' if session['busy'] else run_state(run)
        return experiment_description(run.model.live,run.model.name,run.selected_jobs,phase)
    return experiment_description(live=kind=='Live OpenAI (paid)',count=count)


def start_described(kind, count, speed, request: gr.Request):
    previous=get_session(request)['run']
    for workshop,status in start(kind,count,speed,request):
        run=get_session(request)['run']
        phase=run_state(run) if run and (run.completed or run.error or status=='Stopped.') else 'running'
        description=experiment_description(run.model.live,run.model.name,run.selected_jobs,phase) if run is not None and run is not previous else experiment_description(live=kind=='Live OpenAI (paid)',count=count)
        yield workshop,status,description


def reset_described(kind, count, request: gr.Request):
    _,status=reset(request)
    return render(selected_jobs=int(count)),status,describe_experiment(kind,count,request)


def replay_described(speed, request: gr.Request):
    for workshop,status in replay(speed,request):
        run=get_session(request)['run']
        phase=run_state(run) if status.startswith('Replay ended') else 'replay'
        yield workshop,status,experiment_description(run.model.live,run.model.name,run.selected_jobs,phase)


def build_app():
    with gr.Blocks(title='Groundhog Day • Robot Repair Shop',analytics_enabled=False) as app:
        with gr.Accordion('About this experiment · what are we comparing?',open=False):
            explanation=gr.HTML(experiment_description())
        gr.Markdown('### Workshop controls\nOffline rehearsal is free. Live mode uses your server-side configured OpenAI model and key. One shift uses identical jobs in all three bays.')
        with gr.Row():
            kind=gr.Radio(['Offline scripted demo','Live OpenAI (paid)'],value='Offline scripted demo',label='Engine')
            count=gr.Slider(1,10,value=3,step=1,label='First N jobs per bay · live maximum 4')
            speed=gr.Slider(0.05,0.8,value=0.15,step=0.05,label='Replay / animation beat (seconds)')
        with gr.Row():
            go=gr.Button('Start shift',variant='primary'); halt=gr.Button('Stop'); again=gr.Button('Replay last shift'); clear=gr.Button('Reset workshop')
        status=gr.Textbox(value='Ready · offline mode · no API calls',label='Shift status',interactive=False)
        with gr.Accordion('Share results · portable HTML, JSON and CSV',open=False):
            gr.Markdown('After the shift ends, prepare a report. HTML opens on any computer without the app or an API key. JSON contains configuration and results; CSV contains the job ledger. Review model-generated memory in the HTML before sharing. Local copies also persist in runs/.')
            download=gr.Button('Prepare results downloads')
            files=gr.File(label='Download this shift',file_count='multiple',interactive=False)
        workshop=gr.HTML(render(selected_jobs=3))
        download.click(download_results,[],files,api_visibility='private')
        go.click(lambda: None,[],files,queue=False,api_visibility='private')
        clear.click(lambda: None,[],files,queue=False,api_visibility='private')
        kind.change(describe_experiment,[kind,count],explanation,queue=False,api_visibility='private')
        count.change(describe_experiment,[kind,count],explanation,queue=False,api_visibility='private')
        go.click(start_described,[kind,count,speed],[workshop,status,explanation],concurrency_limit=1,api_visibility='private')
        halt.click(stop,[],status,queue=False,api_visibility='private')
        clear.click(reset_described,[kind,count],[workshop,status,explanation],queue=False,api_visibility='private')
        again.click(replay_described,[speed],[workshop,status,explanation],concurrency_limit=1,api_visibility='private')
    return app

if __name__=='__main__':
    build_app().queue(max_size=8).launch(server_name='127.0.0.1',server_port=7860,share=False,
        css=CSS,theme=gr.themes.Base(primary_hue='lime',neutral_hue='slate'),show_error=False,
        blocked_paths=[str(__import__('pathlib').Path(__file__).resolve().parents[1]/'.env')])
