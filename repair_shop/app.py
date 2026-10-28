"""Local-only Gradio workshop. Explicit live opt-in; offline mode is the default."""
import os
os.environ['GRADIO_ANALYTICS_ENABLED']='False'
import threading
import time
import queue
from copy import deepcopy
from .reports import export, run_state
import gradio as gr
from .engine import Run, LABELS
from .model import DemoModel, OpenAIModel, ModelError
from .world import JOBS
from .view import CSS, render, experiment_description, event_label

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
            raise gr.Error('A shift is running. Wait for it to finish, or stop it first.')
        session['busy']=True
        session['stop']=threading.Event()
    live=kind=='Live OpenAI (paid)'
    try:
        count=int(count)
        if live and count>4:
            raise ModelError('OpenAI runs allow up to 4 jobs per bay (12 repair attempts total). Choose 4 or fewer.')
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
                run.error='The workshop hit an error and stopped. Token and cost totals may be incomplete.'
                run.stop.set()
            finally:
                messages.put(None)
                with LOCK:
                    if abandoned.is_set(): session['busy']=False
        yield render(live=live,model=model.name,running=True,selected_jobs=count), 'Shift started.'
        worker=threading.Thread(target=work,daemon=True); worker.start()
        shown=[]; rs=[]; calls=[]; last_event=time.monotonic()
        try:
            while True:
                try: message=messages.get(timeout=1)
                except queue.Empty:
                    elapsed=int(time.monotonic()-last_event)
                    yield render(shown,rs,live,model.name,True,selected_jobs=count,elapsed=elapsed,calls=calls), f'Running · {len(rs)}/{count*3} attempts ended · {elapsed}s since the last update.'
                    continue
                if message is None: break
                event,rs,calls=message; shown.append(event); last_event=time.monotonic()
                yield render(shown,rs,live,model.name,True,selected_jobs=count,calls=calls), f"{event_label(event['kind'],live)} · {LABELS[event['mode']]} · job {event['job']} · {len(rs)}/{count*3} attempts ended"
            # Persist safe exports locally so a browser refresh does not erase the only copy.
            export(run)
            status='The shift stopped after an error. See the details below; totals may be incomplete.' if run.error else 'Stopped.' if not run.completed else 'Shift complete. Download the results or replay the shift for free.'
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
    return 'Stop requested. If a model request is running, the app will record its usage before stopping. No new requests will start.'

def reset(request: gr.Request):
    session=get_session(request)
    if session['busy']:
        session['stop'].set()
        raise gr.Error('Stopping the shift. Select Reset again after it stops.')
    session['run']=None
    return render(selected_jobs=3), 'Ready for a new shift. All bay memories are cleared.'

def replay(speed, request: gr.Request):
    session=get_session(request)
    with LOCK:
        if session['busy']: raise gr.Error('Wait for the shift to finish or stop.')
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
            yield render(shown,rs,run.model.live,run.model.name,True,selected_jobs=run.selected_jobs,state='replay'), 'Replaying the previous shift · no model calls'
            time.sleep(float(speed))
        yield render(run.events,run.results,run.model.live,run.model.name,False,run.error,selected_jobs=run.selected_jobs,state=run_state(run),calls=run.calls), 'Replay ended · no model calls'
    finally:
        with LOCK: session['busy']=False

def download_results(request: gr.Request):
    session=get_session(request)
    if session['busy']: raise gr.Error('Wait for the shift to finish or stop before downloading results.')
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
        with gr.Accordion('About the experiment',open=False):
            explanation=gr.HTML(experiment_description())
        gr.Markdown('### Run a shift\nTry the free demo or use your configured OpenAI model. Each bay gets the same jobs. Your API key is kept out of the browser and reports.')
        with gr.Row():
            kind=gr.Radio([('Free demo','Offline scripted demo'),('OpenAI (paid)','Live OpenAI (paid)')],value='Offline scripted demo',label='Run mode')
            count=gr.Slider(1,10,value=3,step=1,label='Jobs per bay (OpenAI: up to 4)')
            speed=gr.Slider(0.05,0.8,value=0.15,step=0.05,label='Demo and replay delay (seconds)')
        with gr.Row():
            go=gr.Button('Start shift',variant='primary'); halt=gr.Button('Stop'); again=gr.Button('Replay last shift'); clear=gr.Button('Reset workshop')
        status=gr.Textbox(value='Ready · free demo selected',label='Shift status',interactive=False)
        with gr.Accordion('Download and share results',open=False):
            gr.Markdown('Choose Create report after the shift ends. Open the HTML report in a browser, use the CSV in a spreadsheet, or use the JSON for further analysis. The HTML includes the saved memory notes; review them before sharing. Reports contain no API key.')
            download=gr.Button('Create report')
            files=gr.File(label='Report files',file_count='multiple',interactive=False)
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
