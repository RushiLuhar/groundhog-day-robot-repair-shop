"""Experiment editor and saved runs. Configuration data never includes credentials."""
import json
import queue
import threading
import time
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import gradio as gr
from .config import ExperimentConfig, MechanicConfig, BAY_IDS, MODEL_EFFORTS, POLICIES
from .tasks import SUITES, get_suite
from .storage import ExperimentStore
from .engine import Run, LABELS
from .model import ModelError
from .view import render, configuration_description, event_label, esc
from .reports import export, run_state
from .recovery import recover_report


def selection_description(task,jobs):
    total=len(get_suite(task).jobs)
    return f'**{min(int(jobs),total)} of {total} jobs selected per mechanic, per shift.** Jobs run in their listed order.'


def final_status(run):
    status=run.error or ('Run complete.' if run.completed else run.stop_reason or 'Run stopped.')
    if run.persistence_error:
        status+=' '+run.persistence_error
    else:
        status+=' Results and exact settings are saved locally.'
    if run.export_error: status+=' '+run.export_error
    return status


def store(): return ExperimentStore()

def choices():
    return [(f"{r['name']} · v{r['version']} · {r['config_id'][:6]}",f"{r['config_id']}:{r['version']}") for r in store().list_configs()]

def history_choices():
    return [(f"{r['started_at'][:19]} · {r['status']} · {r['run_id'][:8]}",r['run_id']) for r in store().list_runs()]

def experiment_values(c):
    return [c.name,c.annotation,c.task_set,c.jobs_per_bay,c.repetitions,c.live,c.max_total_tokens]

def mechanic_values(c,bay):
    m=next(m for m in c.mechanics if m.bay_id==bay)
    return [m.name,m.model,gr.Dropdown(choices=MODEL_EFFORTS[m.model],value=m.reasoning),m.memory,
            m.notebook_exchanges,m.memory_tokens,m.step_limit,m.repair_output_tokens,m.memory_output_tokens,m.annotation,m.memory_update_policy]

def collect(draft,name,notes,task,jobs,repeats,live,limit):
    return replace(ExperimentConfig.from_dict(draft),name=name,annotation=notes,task_set=task,
        jobs_per_bay=min(int(jobs),len(get_suite(task).jobs)),repetitions=int(repeats),live=live,max_total_tokens=int(limit)).validate()

def selected_reference(c,ref):
    if ref and store().load_config(ref['id'],ref['version']).to_dict()==c.to_dict(): return ref
    return None

def show_run(run,running=False,events=None,results=None,calls=None,elapsed=0,state=None):
    return render(run.events if events is None else events,run.results if results is None else results,
        run.experiment.live,'per-mechanic settings',running,error=run.error,selected_jobs=run.selected_jobs,
        state=state,elapsed=elapsed,calls=run.calls if calls is None else calls,experiment=run.experiment.to_dict(),
        usage_complete=run.usage_complete,warnings=[run.persistence_error,run.export_error])

def execute(c,ref,speed,request):
    from .app import get_session,LOCK
    session=get_session(request)
    with LOCK:
        if session['busy']: raise gr.Error('A run is already active. Stop it or wait for it to finish.')
        session['busy']=True; session['stop']=threading.Event()
    worker=None
    abandoned=threading.Event()
    try:
        run=Run(stop=session['stop'],experiment=c)
        run.selected_jobs=c.jobs_per_bay
        run.config_reference=selected_reference(c,ref)
        db=store(); db.begin_run(run,run.config_reference)
        session['run']=run
        messages=queue.Queue()
        run.on_checkpoint=lambda r:db.checkpoint(r)
        def on_event(event):
            if event['kind']=='invoice': db.checkpoint(run)
            messages.put((event,deepcopy(run.results),deepcopy(run.calls)))
            if not c.live and not run.stop.is_set(): time.sleep(float(speed))
        run.on_event=on_event
        def work():
            try:
                for _ in run.run(): pass
            except Exception:
                run.error=run.error or 'The run stopped after a local error. Returned usage is retained; do not retry an uncertain paid request.'
                run.interrupt('Execution interrupted by a local error; known usage is retained.')
            finally:
                try:
                    db.checkpoint(run,final=True)
                except Exception:
                    run.persistence_error='Saving the run checkpoint failed. Keep this page open and create a report.'
                try:
                    export(run)
                except Exception:
                    run.export_error='Report export failed. Keep this page open and try Create report.'
                if run.export_error:
                    try: db.checkpoint(run,final=True)
                    except Exception:
                        run.persistence_error='Saving the run checkpoint failed. Keep this page open and create a report.'
                messages.put(None)
                with LOCK:
                    if abandoned.is_set(): session['busy']=False
        worker=threading.Thread(target=work,daemon=True); worker.start()
        shown=[]; results=[]; calls=[]; last=time.monotonic()
        while True:
            try: message=messages.get(timeout=1)
            except queue.Empty:
                yield show_run(run,True,shown,results,calls,int(time.monotonic()-last)),f'Running · {len(results)}/{c.attempts} attempts ended',configuration_description(c)
                continue
            if message is None: break
            event,results,calls=message;shown.append(event);last=time.monotonic()
            yield show_run(run,True,shown,results,calls),f"{event_label(event['kind'],c.live)} · repeat {event['repetition']} · job {event['job']} · {len(results)}/{c.attempts} attempts ended",configuration_description(c)
        status=final_status(run)
        yield show_run(run,state=run_state(run)),status,configuration_description(c)
    except (ValueError,ModelError) as e:
        raise gr.Error(str(e)) from None
    finally:
        abandoned.set()
        if worker and worker.is_alive(): session['stop'].set()
        else:
            with LOCK: session['busy']=False


class SavedRun:
    """Read-only report adapter. Loading results constructs no model or client."""
    def __init__(self,data,status=None):
        data=recover_report(data,uncertain=bool(data.get('live'))) if status=='running' else deepcopy(data)
        self.data=data
        for k in ('events','results','calls','error','selected_jobs','completed','started_at'):
            setattr(self,k,data[k])
        self.id=data['run_id'];self.experiment=ExperimentConfig.from_dict(data['configuration'])
        self.suite=get_suite(self.experiment.task_set);self.cap=data['cap']
        self.model=SimpleNamespace(name=data['model'],live=data['live'])
        self.interrupted=data.get('interrupted',False)
        self.usage_complete=data.get('usage_complete',not bool(data.get('error')))
        self.persistence_error=data.get('persistence_error','')
        self.export_error=data.get('export_error','')
    def report(self):
        return {**deepcopy(self.data),'persistence_error':self.persistence_error,'export_error':self.export_error}
    def totals(self): return deepcopy(self.data['usage'])


def build_app():
    from .app import get_session, stop, download_results
    initial=ExperimentConfig()
    with gr.Blocks(title='Groundhog Day • Robot Repair Shop',analytics_enabled=False) as app:
        draft=gr.State(initial.to_dict()); reference=gr.State(None)
        with gr.Accordion('About the displayed experiment',open=False):
            explanation=gr.HTML(configuration_description(initial))
        gr.Markdown('### Experiment setup\nChoose the jobs and run settings. Click a robot below to edit that mechanic. Settings apply to the next run; displayed results keep their original settings.')
        with gr.Accordion('Save or load an experiment',open=False):
            saved=gr.Dropdown(choices=choices(),label='Saved configuration versions')
            with gr.Row():
                load=gr.Button('Load version');save=gr.Button('Save new version');save_new=gr.Button('Save as new experiment');refresh=gr.Button('Refresh saved lists')
            saved_status=gr.Textbox(label='Configuration status',value='Unsaved draft',interactive=False)
        with gr.Row():
            name=gr.Textbox(label='Experiment name',value=initial.name)
            task=gr.Dropdown(choices=[(s.title,s.id) for s in SUITES.values()],value=initial.task_set,label='Task set')
        notes=gr.Textbox(label='Experiment notes / hypothesis',lines=2)
        with gr.Row():
            jobs=gr.Slider(1,10,value=3,step=1,label='Jobs per mechanic, per shift')
            repeats=gr.Slider(1,10,value=1,step=1,label='Repeated shifts (fresh memory each time)')
            live=gr.Checkbox(value=False,label='Use OpenAI (paid calls)')
        selection=gr.Markdown(selection_description(initial.task_set,initial.jobs_per_bay))
        all_jobs=gr.Button('Select all jobs in this task set')
        with gr.Accordion('Run limits and animation speed',open=False):
            limit=gr.Number(value=500000,precision=0,label='Stop after this many reported tokens (whole run)')
            speed=gr.Slider(.01,.8,value=.05,step=.01,label='Free demo / replay delay (seconds)')
        fields=[name,notes,task,jobs,repeats,live,limit]
        with gr.Row():
            go=gr.Button('Start experiment',variant='primary');halt=gr.Button('Stop');again=gr.Button('Replay displayed run');clear=gr.Button('Reset workshop')
        status=gr.Textbox(label='Run status',value='Ready · free demo selected',interactive=False)
        with gr.Accordion('Saved runs and shareable reports',open=False):
            gr.Markdown('Run results stay on this computer. Load a saved run to inspect or replay it without model calls. A run marked “running” after a restart may have been interrupted; it is never resumed automatically. Review annotations and memory notes before sharing reports.')
            history=gr.Dropdown(choices=history_choices(),label='Saved runs')
            view=gr.Button('View saved run');download=gr.Button('Create report')
            files=gr.File(label='HTML / JSON / CSV reports',file_count='multiple',interactive=False)
        workshop=gr.HTML(render(selected_jobs=3,experiment=initial.to_dict()),js_on_load="""element.addEventListener('click', (event) => { const button=event.target.closest('[data-bay]'); if(button) trigger('click', {bay:button.dataset.bay}); });""")
        with gr.Accordion('Mechanic settings — edit, then apply',open=False,elem_id='mechanic-settings') as editor:
            bay=gr.Dropdown(choices=[('Bay 1','groundhog'),('Bay 2','notebook'),('Bay 3','structured')],value='groundhog',label='Mechanic bay')
            with gr.Row():
                mname=gr.Textbox(label='Mechanic name',value=initial.mechanics[0].name,elem_id='mechanic-name')
                model=gr.Dropdown(choices=list(MODEL_EFFORTS),value='gpt-6-luna',label='OpenAI model')
                reasoning=gr.Dropdown(choices=MODEL_EFFORTS['gpt-6-luna'],value='default',label='Reasoning effort')
            memory=gr.Dropdown(choices=[(LABELS[p],p) for p in POLICIES],value='groundhog',label='Memory between jobs')
            with gr.Row():
                window=gr.Slider(0,100,value=12,step=1,label='Raw notebook: retained action/result exchanges')
                budget=gr.Number(value=1000,precision=0,label='Structured notes: token budget')
                steps=gr.Slider(1,40,value=12,step=1,label='Maximum tool steps per attempt')
            with gr.Row():
                repair_tokens=gr.Number(value=1024,precision=0,label='Repair response: maximum output tokens')
                memory_tokens=gr.Number(value=1600,precision=0,label='Memory response: maximum output tokens')
            mnotes=gr.Textbox(label='Mechanic notes',lines=2)
            update_policy=gr.Dropdown(choices=[('Merge validated records (v2)','merge_v2'),('Replace all notes (legacy v1)','replace_v1')],value='merge_v2',label='Structured memory update policy')
            apply=gr.Button('Apply mechanic settings');mstatus=gr.Markdown('Changes here take effect when you select Apply mechanic settings.')
        mfields=[mname,model,reasoning,memory,window,budget,steps,repair_tokens,memory_tokens,mnotes,update_policy]

        def edit_mechanic(d,b): return mechanic_values(ExperimentConfig.from_dict(d),b)
        def clicked(d,evt:gr.EventData):
            b=getattr(evt,'bay',None)
            if b not in BAY_IDS: return [gr.skip()]*(len(mfields)+2)
            return [b,gr.Accordion(open=True),*edit_mechanic(d,b)]
        selected=workshop.click(clicked,[draft],[bay,editor,*mfields],queue=False,api_visibility='private')
        # Gradio's scroll_to_output does not bring this dynamically opened accordion
        # into view reliably. Wait for its output to render, then reveal and focus it.
        selected.then(fn=None,inputs=[],outputs=[],queue=False,js="""async () => {
            await new Promise(requestAnimationFrame);
            const panel = document.getElementById('mechanic-settings');
            if (!panel) return;
            panel.scrollIntoView({block: 'start', behavior: 'instant'});
            const field = panel.querySelector('#mechanic-name textarea, #mechanic-name input');
            if (field) field.focus({preventScroll: true});
        }""",api_visibility='private')
        bay.input(edit_mechanic,[draft,bay],mfields,queue=False,api_visibility='private')
        model.input(lambda m:gr.Dropdown(choices=MODEL_EFFORTS[m],value='default'),model,reasoning,queue=False,api_visibility='private')
        def apply_mechanic(d,b,n,m,r,p,w,budget,steps,out,mem,annotation,policy):
            try:
                c=ExperimentConfig.from_dict(d)
                setting=MechanicConfig(b,n,m,r,p,int(w),int(budget),int(steps),int(out),int(mem),annotation,memory_update_policy=policy).validate()
                c=replace(c,mechanics=tuple(setting if x.bay_id==b else x for x in c.mechanics)).validate()
                return c.to_dict(),f'Applied settings for {n}. Save a version to keep this configuration.'
            except ValueError as e: raise gr.Error(str(e)) from None
        applied_event=apply.click(apply_mechanic,[draft,bay,*mfields],[draft,mstatus],api_visibility='private')
        def changed(d,n,a,t,j,r,l,cap,request:gr.Request):
            values=(n,a,t,j,r,l,cap)
            try: c=collect(d,*values)
            except ValueError as e: raise gr.Error(str(e)) from None
            session=get_session(request)
            if session['run'] is not None: return c.to_dict(),gr.skip(),gr.skip(),gr.skip()
            return c.to_dict(),render(live=c.live,selected_jobs=c.jobs_per_bay,experiment=c.to_dict()),'Ready · OpenAI selected (paid)' if c.live else 'Ready · free demo selected',configuration_description(c)
        for field in fields:
            field.input(changed,[draft,*fields],[draft,workshop,status,explanation],queue=False,api_visibility='private')
        def applied(d,request:gr.Request):
            c=ExperimentConfig.from_dict(d)
            if get_session(request)['run'] is not None: return gr.skip(),gr.skip()
            return render(live=c.live,selected_jobs=c.jobs_per_bay,experiment=c.to_dict()),configuration_description(c)
        applied_event.then(applied,[draft],[workshop,explanation],api_visibility='private')
        def save_config(d,ref,*values,new=False):
            try:
                c=collect(d,*values)
                result=store().save_config(c,None if new or not ref else ref['id'],None if new or not ref else ref['version'])
                return c.to_dict(),result,gr.Dropdown(choices=choices(),value=f"{result['id']}:{result['version']}"),f"Saved {c.name} · version {result['version']}. Past versions and runs are unchanged."
            except ValueError as e: raise gr.Error(str(e)) from None
        save.click(save_config,[draft,reference,*fields],[draft,reference,saved,saved_status],api_visibility='private')
        def new_config(d,ref,*values): return save_config(d,ref,*values,new=True)
        save_new.click(new_config,[draft,reference,*fields],[draft,reference,saved,saved_status],api_visibility='private')
        def load_config(selection,b):
            if not selection: raise gr.Error('Select a saved configuration version first.')
            ident,version=selection.split(':');ref={'id':ident,'version':int(version)}
            c=store().load_config(ident,int(version))
            return [c.to_dict(),ref,*experiment_values(c),*mechanic_values(c,b),f'Loaded {c.name} · version {version}. Select Start experiment to run it.']
        loaded=load.click(load_config,[saved,bay],[draft,reference,*fields,*mfields,saved_status],api_visibility='private')
        loaded.then(applied,[draft],[workshop,explanation],api_visibility='private')
        loaded.then(lambda t:gr.Slider(maximum=len(get_suite(t).jobs)),task,jobs,api_visibility='private')
        task.input(lambda t,j:gr.Slider(maximum=len(get_suite(t).jobs),value=min(int(j),len(get_suite(t).jobs))),[task,jobs],jobs,queue=False,api_visibility='private')
        for field in (task,jobs):
            field.change(selection_description,[task,jobs],selection,queue=False,api_visibility='private')
        def select_all(d,n,a,t,j,r,l,cap,request:gr.Request):
            count=len(get_suite(t).jobs)
            updated=changed(d,n,a,t,count,r,l,cap,request)
            return gr.Slider(maximum=count,value=count),*updated
        all_jobs.click(select_all,[draft,*fields],[jobs,draft,workshop,status,explanation],api_visibility='private')
        refresh.click(lambda:(gr.Dropdown(choices=choices()),gr.Dropdown(choices=history_choices())),[],[saved,history],api_visibility='private')
        def start(d,ref,delay,n,a,t,j,r,l,cap,request:gr.Request):
            values=(n,a,t,j,r,l,cap)
            try:c=collect(d,*values)
            except ValueError as e:raise gr.Error(str(e)) from None
            yield from execute(c,ref,delay,request)
        started=go.click(start,[draft,reference,speed,*fields],[workshop,status,explanation],concurrency_limit=1,api_visibility='private')
        started.then(lambda:gr.Dropdown(choices=history_choices()),[],history,api_visibility='private')
        halt.click(stop,[],status,queue=False,api_visibility='private')
        def reset(d,n,a,t,j,r,l,cap,request:gr.Request):
            values=(n,a,t,j,r,l,cap)
            session=get_session(request)
            if session['busy']:
                session['stop'].set(); raise gr.Error('Stop requested. Reset again after the run ends.')
            session['run']=None;c=collect(d,*values)
            return render(live=c.live,selected_jobs=c.jobs_per_bay,experiment=c.to_dict()),'Ready · OpenAI selected (paid)' if c.live else 'Ready · free demo selected',configuration_description(c)
        clear.click(reset,[draft,*fields],[workshop,status,explanation],queue=False,api_visibility='private')
        def view_saved(identifier,request:gr.Request):
            session=get_session(request)
            if session['busy']:raise gr.Error('Wait for the active run or stop it first.')
            if not identifier:raise gr.Error('Select a saved run.')
            row=store().load_run(identifier)
            if not row['report']:raise gr.Error('This run stopped before its first checkpoint. No results are available; no requests were retried.')
            run=SavedRun(row['report'],row['status']);session['run']=run
            return show_run(run,state=run_state(run)),f"Saved run · {row['status']} · {identifier[:8]} · no model calls",configuration_description(run.experiment)
        view.click(view_saved,[history],[workshop,status,explanation],api_visibility='private')
        def replay(delay,request:gr.Request):
            from .app import LOCK
            session=get_session(request)
            with LOCK:
                if session['busy']:raise gr.Error('Wait for the run or stop it first.')
                run=session['run']
                if run is None:raise gr.Error('Run an experiment or load saved results first.')
                session['busy']=True;session['stop']=threading.Event()
            try:
                shown=[]
                for e in run.events:
                    if session['stop'].is_set():break
                    shown.append(e)
                    settled={(x.get('repetition',1),x['mode'],x['job']) for x in shown if x['kind']=='invoice'}
                    rs=[r for r in run.results if (r.get('repetition',1),r['mode'],r['job']) in settled]
                    yield show_run(run,True,shown,rs,[],state='replay'),'Replaying saved events · no model calls',configuration_description(run.experiment)
                    time.sleep(float(delay))
                yield show_run(run,state=run_state(run)),'Replay ended · no model calls',configuration_description(run.experiment)
            finally:
                with LOCK:session['busy']=False
        again.click(replay,[speed],[workshop,status,explanation],api_visibility='private')
        download.click(download_results,[],files,api_visibility='private')
        app.load(lambda:(gr.Dropdown(choices=choices()),gr.Dropdown(choices=history_choices())),[],[saved,history],api_visibility='private')
        for action in (go,clear,view):
            action.click(lambda:None,[],files,queue=False,api_visibility='private')
    return app
