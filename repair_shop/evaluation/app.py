"""Local comparison and trace UI. The legacy workshop is a separate entry point."""
import os
os.environ['GRADIO_ANALYTICS_ENABLED']='False'
import json,queue,threading,time
from copy import deepcopy
from pathlib import Path
import gradio as gr
from .config import EvaluationConfig,preset
from .runner import EvaluationRun
from .storage import Store,DEFAULT
from .reporting import render,export,CSS,esc


def parse(text):
    try:return EvaluationConfig.from_dict(json.loads(text))
    except (ValueError,TypeError) as e:raise gr.Error(str(e)) from None

def describe(c):
    lines=[f'### {c.name}',f'**Task: {c.task_set} / {c.variant}. {len(c.conditions)} conditions × {c.jobs} of 8 tickets × {c.repetitions} repetitions = {c.attempts} attempts.**',
        f'Run token safety limit: {c.run_total_token_limit:,}. Estimated USD safety limit: {c.run_estimated_usd_limit if c.run_estimated_usd_limit is not None else "disabled explicitly"}. Admission policy: {c.request_admission_policy}.',
        'Condition order rotates across fresh repetitions; ticket order stays fixed. Current-job raw results and literal logs are identical context policies across conditions. Writer runs once at job end only for structured memory. Limits check returned usage; one request may overshoot. No automatic retry.',
        '| Condition / memory | Repair: model / effort / prompt / output cap | Writer: model / effort / prompt / output cap | Entries / retained tokens / supplied tokens | Tool steps / total job tokens |',
        '| --- | --- | --- | --- | --- |']
    for cnd in c.conditions:
        a=cnd.repair;w=cnd.writer
        lines.append(f'| {cnd.id} / {cnd.memory} | {a.model} / {a.reasoning} / {a.prompt_version} / {a.response_output_cap} | {w.model} / {w.reasoning} / {w.prompt_version} / {w.response_output_cap} ({"active" if cnd.memory=="structured" else "inactive"}) | {cnd.rolling_entry_limit} / {cnd.retention_tokens} / {cnd.supply_tokens} | {cnd.tool_step_limit} / {cnd.job_total_token_allowance} |')
    lines.append('Equal token limits are not equal dollar costs. Presets isolate repair settings while holding writer configuration fixed. Scripted results are mechanism checks, not model comparisons.')
    return '\n\n'.join(lines[:4])+'\n\n'+'\n'.join(lines[4:-1])+'\n\n'+lines[-1]

class Controller:
    def __init__(self,store=None,export_directory=None,agent_factory=None):
        self.store=store or Store();self.export_directory=Path(export_directory or DEFAULT.parent/'evaluation-reports')
        self.agent_factory=agent_factory;self.sessions={};self.lock=threading.Lock()
    def session(self,request):
        with self.lock:return self.sessions.setdefault(request.session_hash,{'busy':False,'run':None,'saved':None,'stop':threading.Event()})
    def config_choices(self):return [(f'{name} · v{v}',f'{i}:{v}') for i,v,name in self.store.configs()]
    def run_choices(self):return [(f'{i[:8]} · {state}',i) for i,state in self.store.runs()]
    def start(self,text,paid,request:gr.Request):
        c=parse(text)
        if c.live and not paid:raise gr.Error('This configuration requests paid calls. Explicit paid opt-in is required; offline is the default.')
        s=self.session(request)
        with self.lock:
            if s['busy']:raise gr.Error('A run or replay is active. Stop it and wait before starting again.')
            s['busy']=True;s['stop']=threading.Event()
        messages=queue.Queue();worker=None
        try:
            run=EvaluationRun(c,stop=s['stop'],agent_factory=self.agent_factory,on_checkpoint=self.store.checkpoint)
            self.store.begin(run);s['run']=run;s['saved']=None
            run.on_event=lambda e:messages.put(True)
            def work():
                try:list(run.run())
                finally:
                    try:export(run.report(),self.export_directory)
                    except Exception:run.export_error='Report export failed; use Create report to retry export only.'
                    try:self.store.checkpoint(run)
                    except Exception:run.persistence_error='Final checkpoint failed; keep this page and export known evidence.'
                    with self.lock:s['busy']=False
                    messages.put(None)
            worker=threading.Thread(target=work,daemon=True);worker.start()
            while True:
                try:d=messages.get(timeout=1)
                except queue.Empty:
                    yield render(run.report()),'Running · waiting for returned usage',describe(c),gr.skip();continue
                if d is None:break
                # Coalesce progress notifications; do not queue full growing trace snapshots.
                while not messages.empty():
                    d=messages.get_nowait()
                    if d is None:break
                if d is None:break
                d=run.report()
                yield render(d),'Running · '+d['state'],describe(c),gr.skip()
            d=run.report()
            status=' · '.join(x for x in (d['state'],d['error'] or d['stop_reason'],d['persistence_error'],d['export_error']) if x)
            yield render(d),status,describe(c),gr.Dropdown(choices=self.run_choices(),value=run.id)
        finally:
            if worker and worker.is_alive():s['stop'].set()
            else:
                with self.lock:s['busy']=False
    def stop(self,request:gr.Request):
        self.session(request)['stop'].set()
        return 'Stop requested. Awaiting any in-flight usage; no automatic retry.'
    def reset(self,request:gr.Request):
        s=self.session(request)
        if s['busy']:
            s['stop'].set();raise gr.Error('Stop requested. Reset again after execution finishes.')
        s['run']=None;s['saved']=None
        return render(None),'Ready · offline by default',None
    def load_run(self,ident,request:gr.Request):
        s=self.session(request)
        if s['busy']:raise gr.Error('Stop or wait before loading historical results.')
        if not ident:raise gr.Error('Select a saved run.')
        d=self.store.load(ident);s['saved']=d;s['run']=None
        return render(d),'Read-only saved run · '+d['state'],describe(EvaluationConfig.from_dict(d['manifest']['config']))
    def data(self,s):return s['run'].report() if s['run'] else deepcopy(s['saved'])
    def download(self,request:gr.Request):
        s=self.session(request)
        if s['busy']:raise gr.Error('Wait for the run or stop before exporting.')
        d=self.data(s)
        if not d:raise gr.Error('Run or load an evaluation first.')
        d['export_error']=''
        try:paths=export(d,self.export_directory)
        except Exception:raise gr.Error('Export failed; execution evidence remains in memory.') from None
        if s['run']:
            s['run'].export_error=''
            try:self.store.checkpoint(s['run'])
            except Exception:s['run'].persistence_error='Export succeeded; updating the saved export status failed.'
        else:s['saved']['export_error']=''
        return paths
    def replay(self,request:gr.Request):
        s=self.session(request)
        with self.lock:
            if s['busy']:raise gr.Error('A run or replay is active.')
            d=self.data(s)
            if not d:raise gr.Error('Run or load an evaluation first.')
            s['busy']=True;s['stop']=threading.Event()
        try:
            for e in d['events']:
                if s['stop'].is_set():break
                yield '<h2>Replay · no model calls</h2><p>Recorded final outcomes remain below; this is event '+str(e['sequence'])+'.</p><pre>'+esc(json.dumps(e,indent=2))+'</pre>'+render(d),'Replay · no model calls'
                time.sleep(.01)
            yield render(d),'Replay ended · no model calls'
        finally:
            with self.lock:s['busy']=False
    def save_config(self,text,ref,new):
        c=parse(text);ref=self.store.save_config(c,None if new else ref)
        return ref,gr.Dropdown(choices=self.config_choices(),value=f'{ref["id"]}:{ref["version"]}'),f'Saved immutable version {ref["version"]}.'
    def load_config(self,key):
        if not key:raise gr.Error('Select a saved configuration.')
        ident,v=key.split(':');ref={'id':ident,'version':int(v)};c=self.store.load_config(ref)
        return json.dumps(c.to_dict(),indent=2),ref,describe(c)


def build_app(controller=None):
    ctl=controller or Controller();initial=preset()
    with gr.Blocks(title='Paired agent evaluations',analytics_enabled=False) as app:
        gr.Markdown('# Paired agent evaluations\nCompare memory, reasoning, models and limits on the same eight tickets. The original robot workshop and historical experiments remain separate. No live pilot has been authorized by this configuration.')
        reference=gr.State(None)
        with gr.Row():
            presets=gr.Dropdown(['memory','reasoning','model','budget','tuned-v2'],value='memory',label='Comparison preset')
            use=gr.Button('Load preset')
        gr.Markdown('Edit the explicit condition list below: add or remove conditions freely. Repair and writer settings, retention/supply limits, per-job allowance and run safety limits have separate names. Start uses the validated text as an immutable snapshot. Loading a preset does not run it.')
        config=gr.Code(value=json.dumps(initial.to_dict(),indent=2),language='json',label='Versioned configuration · editable JSON',lines=18)
        validate=gr.Button('Validate and inspect settings')
        summary=gr.Markdown(describe(initial),elem_classes=['eval-settings'])
        with gr.Accordion('Save or load configuration versions',open=False):
            configs=gr.Dropdown(choices=ctl.config_choices(),label='Saved configurations')
            load=gr.Button('Load configuration');save=gr.Button('Save new version');save_new=gr.Button('Save as new configuration')
            config_status=gr.Textbox(label='Configuration status',interactive=False)
        paid=gr.Checkbox(False,label='Explicitly permit paid calls when configuration live is true')
        with gr.Row():
            start=gr.Button('Start evaluation',variant='primary');stop=gr.Button('Stop');reset=gr.Button('Reset');replay=gr.Button('Replay')
        status=gr.Textbox(value='Ready · offline by default',label='Execution status',interactive=False)
        with gr.Accordion('Saved evaluations and exports',open=False):
            runs=gr.Dropdown(choices=ctl.run_choices(),label='Saved evaluations')
            refresh=gr.Button('Refresh saved lists');load_run=gr.Button('Load saved evaluation');download=gr.Button('Create report')
            files=gr.File(file_count='multiple',label='HTML / JSON / CSV reports',interactive=False)
        results=gr.HTML(render(None))
        validate.click(lambda text:describe(parse(text)),config,summary,api_visibility='private')
        use.click(lambda p:(json.dumps(preset(p).to_dict(),indent=2),None,describe(preset(p))),presets,[config,reference,summary],api_visibility='private')
        save.click(lambda text,ref:ctl.save_config(text,ref,False),[config,reference],[reference,configs,config_status],api_visibility='private')
        save_new.click(lambda text,ref:ctl.save_config(text,ref,True),[config,reference],[reference,configs,config_status],api_visibility='private')
        load.click(ctl.load_config,configs,[config,reference,summary],api_visibility='private')
        start.click(ctl.start,[config,paid],[results,status,summary,runs],concurrency_limit=1,api_visibility='private')
        stop.click(ctl.stop,[],status,queue=False,api_visibility='private')
        reset.click(ctl.reset,[],[results,status,files],queue=False,api_visibility='private')
        replay.click(ctl.replay,[],[results,status],api_visibility='private')
        load_run.click(ctl.load_run,runs,[results,status,summary],api_visibility='private')
        download.click(ctl.download,[],files,api_visibility='private')
        refresh.click(lambda:(gr.Dropdown(choices=ctl.config_choices()),gr.Dropdown(choices=ctl.run_choices())),[],[configs,runs],api_visibility='private')
        app.load(lambda:(gr.Dropdown(choices=ctl.config_choices()),gr.Dropdown(choices=ctl.run_choices())),[],[configs,runs],api_visibility='private')
    return app

if __name__=='__main__':
    build_app().queue(max_size=8).launch(server_name='127.0.0.1',server_port=7862,share=False,css=CSS,
        blocked_paths=[str(Path(__file__).resolve().parents[2]/'.env')],show_error=False)
