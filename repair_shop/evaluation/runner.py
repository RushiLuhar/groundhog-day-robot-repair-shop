"""Sequential paired-condition execution with explicit request/attempt accounting."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from threading import Event
import hashlib,json,subprocess,time,uuid
from ..tasks import get_evaluation_suite
from ..costs import estimate,total_cost,PRICE_DATE,PRICE_URL,COST_NOTE,RATES
from .config import EvaluationConfig,LOG_VERSION,MEMORY_VERSION
from .models import LiveAgent,ScriptedWriter,PROMPTS,request_reservation
from .service import ServiceDemo
from .memory import Memory
from .observations import observation,supplied,tokens


def source_revision():
    root=Path(__file__).resolve().parents[2]
    try:
        sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True,stderr=subprocess.DEVNULL).strip()
        dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True,stderr=subprocess.DEVNULL).strip())
        return {'commit':sha,'dirty':dirty}
    except (OSError,subprocess.CalledProcessError):return {'commit':'unavailable','dirty':None}


def aggregate(calls):
    known=[c for c in calls if c['status']=='returned']
    roles={role:{'input':sum(c['input'] for c in known if c['role']==role),
        'output':sum(c['output'] for c in known if c['role']==role)} for role in ('repair','writer')}
    return {'roles':roles,'input':sum(c['input'] for c in known),'output':sum(c['output'] for c in known),
            'known_calls':len(known),'unknown_calls':sum(c['status']=='unknown' for c in calls),
            'estimated_usd':total_cost(known),'usage_complete':not any(c['status'] in ('pending','unknown') for c in calls)}

class EvaluationRun:
    def __init__(self,config,stop=None,agent_factory=None,on_checkpoint=None,on_event=None,renderer=observation):
        self.config=EvaluationConfig.from_dict(config.to_dict())
        self.suite=get_evaluation_suite(config.task_set,config.variant)
        tokens([]) # Resolve tokenizer before constructing clients or making any request.
        self.id=uuid.uuid4().hex;self.started_at=datetime.now(timezone.utc).isoformat()
        self.stop=stop or Event();self.checkpoint=on_checkpoint;self.on_event=on_event;self.renderer=renderer
        self.state='ready';self.error='';self.stop_reason='';self.persistence_error='';self.export_error=''
        self.calls=[];self.events=[];self.attempts=[];self.memories={};self.active=None
        self._started=None;self.elapsed_seconds=0;self._elapsed_before=0
        self.agents={}
        for c in config.conditions:
            for role in ('repair','writer') if c.memory=='structured' else ('repair',):
                settings=getattr(c,role)
                self.agents[c.id,role]=(agent_factory(settings,role,self.suite) if agent_factory else
                    LiveAgent(settings,role,self.suite) if config.live else ServiceDemo() if role=='repair' else ScriptedWriter())
        self._manifest={'schema_version':2,'config':self.config.to_dict(),'source':source_revision(),
            'task':self.suite.public_description(),'variant':config.variant,'ordered_jobs':[j.number for j in self.suite.jobs[:config.jobs]],
            'condition_order':[c.id for c in config.conditions],'log_version':LOG_VERSION,'memory_version':MEMORY_VERSION,
            'supply_version':'newest-evidence-whole-record-v1','consolidation':'one-job-end-writer-v1',
            'prompts':deepcopy(PROMPTS),'task_instructions':self.suite.instructions,'tools':deepcopy(self.suite.tools),
            'pricing':{'date':PRICE_DATE,'url':PRICE_URL,'note':COST_NOTE,'usd_per_million_input_output':deepcopy(RATES)},
            'service_tier':'default','request_admission_policy':config.request_admission_policy,
            'comparison_note':'Equal token caps are not equal dollar costs. Partial/unequal exposure is not a ranking.'}
        self._manifest['condition_order_by_repetition']=[[c.id for c in config.conditions[(r%len(config.conditions)):]+config.conditions[:(r%len(config.conditions))]] for r in range(config.repetitions)]
        self._manifest=json.loads(json.dumps(self._manifest))
        self._manifest['fingerprint']=hashlib.sha256(json.dumps(self._manifest,sort_keys=True).encode()).hexdigest()
        for rep in range(1,config.repetitions+1):
            for job in self.suite.jobs[:config.jobs]:
                offset=(rep-1)%len(config.conditions)
                for c in config.conditions[offset:]+config.conditions[:offset]:
                    self.attempts.append({'repetition':rep,'condition':c.id,'job':job.number,'status':'unattempted','certified':False,
                        'steps':0,'reason':'','writer_error':'','infrastructure_error':'','logging_error':'','elapsed_seconds':0,
                        'raw_events':[],'observation_log':[],'missing_entries':[],'memory_input':[],
                        'memory_supply_audit':{},'memory_update_audit':{},'writer_output':None,'memory_after':[]})
    @property
    def manifest(self):return deepcopy(self._manifest)
    def emit(self,kind,**fields):
        e={'sequence':len(self.events)+1,'kind':kind,**deepcopy(fields)}
        if self.active is not None:e.update({k:self.active[k] for k in ('condition','repetition','job')})
        self.events.append(e)
        if self.on_event:self.on_event(deepcopy(e))
    def save(self):
        if self.checkpoint:self.checkpoint(self)
    def totals(self,attempt=None):
        calls=self.calls if attempt is None else [c for c in self.calls if all(c[k]==attempt[k] for k in ('condition','repetition','job'))]
        return aggregate(calls)
    def budget_reason(self,c,row):
        total=self.totals();job=self.totals(row)
        if total['input']+total['output']>=self.config.run_total_token_limit:
            self.stop_reason='Run total-token safety limit reached; one returned call may overshoot.';self.stop.set()
        usd=self.config.run_estimated_usd_limit
        if usd is not None and total['estimated_usd'] is not None and total['estimated_usd']>=usd:
            self.stop_reason='Run estimated-USD safety limit reached; one returned call may overshoot.';self.stop.set()
        if self.stop.is_set():return self.stop_reason or 'Stopped by user.'
        if job['input']+job['output']>=c.job_total_token_allowance:return 'Job total-token safety allowance reached.'
        return ''
    def request(self,c,row,role,payload):
        reason=self.budget_reason(c,row)
        if reason:return None,reason
        settings=getattr(c,role);agent=self.agents[c.id,role]
        reservation=None
        if self.config.request_admission_policy=='conservative-bytes-v1':
            reservation=request_reservation(settings,role,self.suite,payload,self.config.live)
            total=self.totals();cap=self.config.run_estimated_usd_limit
            if total['input']+total['output']+reservation['input_tokens']+reservation['output_tokens']>self.config.run_total_token_limit:
                self.stop_reason='Run token admission guard: insufficient allowance for the next bounded request.'
            elif cap is not None and (reservation['estimated_usd'] is None or total['estimated_usd'] is None or total['estimated_usd']+reservation['estimated_usd']>cap):
                self.stop_reason='Run USD admission guard: insufficient known-price allowance for the next bounded request.'
            if self.stop_reason:
                self.stop.set();self.emit('request_not_admitted',role=role,reservation=reservation);self.save()
                return None,self.stop_reason
        call={k:row[k] for k in ('condition','repetition','job')}
        call.update(role=role,model=settings.model,status='pending',input=None,output=None,cost_usd=None,
                    response_status='',end_reason='',reservation=reservation)
        self.calls.append(call)
        try:self.save()
        except Exception:
            call['status']='not_sent'
            raise
        if self.stop.is_set():
            call['status']='not_sent';self.save();return None,self.stop_reason or 'Stopped before request.'
        start=time.monotonic()
        try:
            reply=agent.decide(deepcopy(payload)) if role=='repair' else agent.write(deepcopy(payload))
        except BaseException:
            call['status']='unknown';call['elapsed_seconds']=time.monotonic()-start
            raise
        if any(type(v) is not int or v<0 for v in (reply.input_tokens,reply.output_tokens)):
            call['status']='unknown'
            from ..model import ModelError
            raise ModelError('Missing or invalid returned usage; no retry.')
        call.update(status='returned',input=reply.input_tokens,output=reply.output_tokens,
                    cost_usd=estimate(settings.model,reply.input_tokens,reply.output_tokens,self.config.live),
                    response_status=reply.status,end_reason=reply.end_reason,elapsed_seconds=time.monotonic()-start,
                    provider=deepcopy(getattr(reply,'provider_metadata',{})))
        self.save()
        user_stopped=self.stop.is_set() and not self.stop_reason
        self.budget_reason(c,row)
        if reservation and (reply.input_tokens>reservation['input_tokens'] or reply.output_tokens>reservation['output_tokens']):
            self.stop_reason='Returned usage exceeded the conservative reservation; no further requests.';self.stop.set()
        return reply,'Stopped by user after returned usage.' if user_stopped else ''
    def run(self):
        if self.state!='ready':raise ValueError('A run cannot be resumed or executed twice.')
        self.state='running';self._started=time.monotonic()
        try:
            for row in self.attempts:
                if self.stop.is_set():break
                if row['status']!='unattempted':continue
                self.active=row;c=next(c for c in self.config.conditions if c.id==row['condition'])
                mem=self.memories.setdefault((row['repetition'],c.id),Memory())
                world=self.suite.create_world(self.suite.jobs[row['job']-1])
                row['status']='running';started=time.monotonic()
                prior,audit=mem.supply(c);row['memory_input']=deepcopy(prior);row['memory_supply_audit']=audit
                self.emit('attempt_started',memory_supply_audit=audit);self.save()
                try:
                    while row['steps']<c.tool_step_limit:
                        totals=self.totals(row)
                        context={'ticket':world.job.ticket(),'steps_remaining':c.tool_step_limit-row['steps'],
                            'job_tokens_remaining':max(0,c.job_total_token_allowance-totals['input']-totals['output']),
                            'current_job_results':deepcopy(row['raw_events']),
                            'current_job_log':supplied(row['observation_log']),'missing_log_entries':deepcopy(row['missing_entries']),
                            'prior_memory':deepcopy(prior),
                            'partial_retained_jobs':deepcopy(audit.get('partial_jobs',[]))}
                        self.emit('repair_request')
                        reply,reason=self.request(c,row,'repair',context)
                        if reply is None:row['reason']=reason;break
                        if reason:row['reason']=reason;break
                        if reply.action is None:row['reason']=reply.end_reason or 'No tool action.';break
                        action=reply.action
                        result=world.call(action.get('name'),action.get('arguments',{}));row['steps']+=1
                        eid=f"r{row['repetition']}:{c.id}:j{row['job']}:e{row['steps']}"
                        raw={'entry_id':eid,'job':row['job'],'action':deepcopy(action),'result':deepcopy(result)}
                        row['raw_events'].append(raw)
                        row['certified']=world.passed
                        try:row['observation_log'].append(self.renderer(eid,row['job'],action,result))
                        except Exception:
                            row['missing_entries'].append({'entry_id':eid,'reason':'Unsupported or overlong log result.'})
                            row['logging_error']='Observation format error; raw event retained.'
                            raise
                        self.emit('tool_result',raw_event=raw,log_entry=row['observation_log'][-1])
                        self.save()
                        if world.passed:row['reason']='Independent test passed.';break
                    if not row['reason']:row['reason']='Tool-step cap reached.'
                    row['status']='success' if row['certified'] else 'interrupted' if self.stop.is_set() else 'unfinished'
                    if c.memory!='none':mem.observe(row['observation_log'])
                    if c.memory=='rolling':row['memory_update_audit']=mem.retain_rolling(row['observation_log'],c)
                    if c.memory=='structured':
                        reason=self.budget_reason(c,row)
                        if reason:row['memory_update_audit']={'skipped':reason}
                        else:
                            payload={'ticket':world.job.ticket(),'observation_log':supplied(row['observation_log']),
                                'missing_entries':deepcopy(row['missing_entries']),'previous_records':deepcopy(mem.records),
                                'source_catalog':deepcopy(mem.catalog),'retention_token_limit':c.retention_tokens}
                            self.emit('writer_request')
                            reply,reason=self.request(c,row,'writer',payload)
                            if reply is None:row['memory_update_audit']={'skipped':reason}
                            else:
                                row['writer_output']={'text':reply.text,'status':reply.status,'end_reason':reply.end_reason}
                                try:
                                    if reply.status!='completed':raise ValueError(reply.end_reason or 'Incomplete writer response.')
                                    row['memory_update_audit']=mem.merge(reply.text,c)
                                except (ValueError,TypeError,KeyError) as e:
                                    row['writer_error']='Writer output rejected; previous records retained.'
                                    row['memory_update_audit']={'rejected_response':str(e)}
                    row['memory_after']=deepcopy(mem.records if c.memory=='structured' else supplied(mem.history) if c.memory=='rolling' else [])
                except BaseException as e:
                    is_writer=bool(self.calls and self.calls[-1]['role']=='writer' and all(self.calls[-1][k]==row[k] for k in ('condition','job','repetition')))
                    message='Execution interrupted; an outstanding request may have unknown usage.' if isinstance(e,(KeyboardInterrupt,GeneratorExit)) else 'Infrastructure failure; no automatic retry. Known usage is retained.'
                    # ModelError is deliberately sanitized by the official adapter.
                    from ..model import ModelError
                    if isinstance(e,ModelError):message=str(e)
                    if is_writer:row['writer_error']=message
                    row['infrastructure_error']=message
                    row['status']='success' if row['certified'] else 'interrupted' if isinstance(e,(KeyboardInterrupt,GeneratorExit)) else 'infrastructure_error'
                    row['reason']=row['reason'] or message
                    self.error=message;self.stop.set()
                finally:
                    row['memory_after']=deepcopy(mem.records if c.memory=='structured' else supplied(mem.history) if c.memory=='rolling' else [])
                    row['elapsed_seconds']=time.monotonic()-started
                    row['task_metrics']=world.metrics()
                    self.emit('attempt_ended',status=row['status'],certified=row['certified'])
                    self.save();self.active=None
                yield deepcopy(row)
            self.state='error' if self.error else 'stopped' if self.stop.is_set() else 'completed'
        except BaseException:
            self.error=self.error or 'Local persistence/execution failure; known evidence retained.'
            self.state='error';self.stop.set()
            if self.active and self.active['status']=='running':
                self.active['status']='interrupted';self.active['reason']=self.error
            self.active=None
        finally:
            self.elapsed_seconds=self._elapsed_before+time.monotonic()-self._started
            try:self.save()
            except Exception:self.persistence_error='Final checkpoint failed; export the in-memory report.'
    def report(self):
        rows=deepcopy(self.attempts)
        for r in rows:r['usage']=self.totals(r)
        return {'schema_version':2,'run_id':self.id,'started_at':self.started_at,'state':self.state,
            'manifest':self.manifest,'attempts':rows,'calls':deepcopy(self.calls),'events':deepcopy(self.events),
            'usage':self.totals(),'error':self.error,'stop_reason':self.stop_reason,
            'elapsed_seconds':self._elapsed_before+time.monotonic()-self._started if self.state=='running' and self._started else self.elapsed_seconds,
            'persistence_error':self.persistence_error,'export_error':self.export_error}


def continue_unattempted(report,config,**kwargs):
    """Explicit USD extension only; preserve every started attempt and its charges.

    Creates a new linked run. Never used by startup/UI recovery, never retries a
    partial attempt, and refuses uncertain usage or changes to scientific controls.
    Callers must obtain authorization for the new *combined* ceiling first.
    """
    prior=deepcopy(report)
    def require(ok,message):
        if not ok:raise ValueError(message)
    require(prior['state']=='stopped' and prior['stop_reason'].startswith('Run USD admission guard:'),
            'Only a settled USD-admission stop can be explicitly extended.')
    require(not any(prior.get(k) for k in ('error','persistence_error','export_error')),
            'Failed or uncertain execution cannot be continued.')
    require(all(c['status']=='returned' for c in prior['calls']) and prior['usage']==aggregate(prior['calls']),
            'Continuation requires complete, reconciled returned usage.')
    old=EvaluationConfig.from_dict(prior['manifest']['config']);config.validate()
    changed=config.to_dict();changed['name']=old.name;changed['run_estimated_usd_limit']=old.run_estimated_usd_limit
    require(changed==old.to_dict(),'Only name and the combined USD ceiling may change.')
    require(old.run_estimated_usd_limit is not None and config.run_estimated_usd_limit is not None
            and config.run_estimated_usd_limit>old.run_estimated_usd_limit,'USD ceiling must increase explicitly.')
    manifest=deepcopy(prior['manifest']);fingerprint=manifest.pop('fingerprint')
    require(hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()==fingerprint,
            'Prior manifest fingerprint does not match.')
    # Use offline adapters for validation so malformed input cannot construct a live client.
    factory=kwargs.pop('agent_factory',None)
    run=EvaluationRun(config,agent_factory=lambda settings,role,suite:None,**kwargs)
    for key in ('task','variant','ordered_jobs','condition_order_by_repetition','log_version','memory_version',
                'supply_version','consolidation','prompts','task_instructions','tools','pricing','service_tier','request_admission_policy'):
        require(run.manifest[key]==prior['manifest'][key],'Runtime contract changed: '+key)
    key=lambda r:tuple(r[k] for k in ('repetition','condition','job'))
    require([key(r) for r in run.attempts]==[key(r) for r in prior['attempts']], 'Attempt schedule changed.')
    ended=[(e['repetition'],e['condition'],e['job']) for e in prior['events'] if e['kind']=='attempt_ended']
    started=[r for r in prior['attempts'] if r['status']!='unattempted']
    require(ended==[key(r) for r in started] and len(set(ended))==len(ended),'Started attempts are not settled exactly once.')
    unseen=False
    for row in prior['attempts']:
        if row['status']=='unattempted':
            unseen=True
            require(not row['raw_events'] and row['steps']==0 and not any(key(c)==key(row) for c in prior['calls']),
                    'Unattempted position contains work or charges.')
            continue
        require(not unseen and row['status'] in ('success','unfinished','interrupted'), 'Completed prefix is invalid.')
        require(not any(row[k] for k in ('writer_error','infrastructure_error','logging_error')), 'Errored attempt cannot be continued.')
        require(row['usage']==aggregate([c for c in prior['calls'] if key(c)==key(row)]),'Attempt usage does not reconcile.')
        c=next(c for c in config.conditions if c.id==row['condition'])
        mem=run.memories.setdefault((row['repetition'],c.id),Memory())
        supplied_before,audit=mem.supply(c)
        require(supplied_before==row['memory_input'] and audit==row['memory_supply_audit'],'Memory supply replay differs.')
        world=run.suite.create_world(run.suite.jobs[row['job']-1])
        logs=[]
        for raw in row['raw_events']:
            require(world.call(raw['action']['name'],raw['action']['arguments'])==raw['result'],'Tool replay differs.')
            logs.append(observation(raw['entry_id'],raw['job'],raw['action'],raw['result']))
        require(logs==row['observation_log'] and len(logs)==row['steps'] and world.passed==row['certified'],
                'Observation/certification replay differs.')
        if c.memory!='none':mem.observe(logs)
        if c.memory=='rolling':require(mem.retain_rolling(logs,c)==row['memory_update_audit'],'Rolling retention replay differs.')
        if c.memory=='structured' and row['writer_output']:
            require(mem.merge(row['writer_output']['text'],c)==row['memory_update_audit'],'Writer merge replay differs.')
        restored=mem.records if c.memory=='structured' else supplied(mem.history) if c.memory=='rolling' else []
        require(restored==row['memory_after'],'Retained memory replay differs.')
    require(unseen,'No unattempted positions remain.')
    require(all(key(c) in set(ended) for c in prior['calls']),'Call is outside the completed prefix.')
    run.attempts=deepcopy(prior['attempts'])
    for row in run.attempts:row.pop('usage',None)
    run.calls=deepcopy(prior['calls']);run.events=deepcopy(prior['events'])
    run._elapsed_before=prior['elapsed_seconds'];run.elapsed_seconds=run._elapsed_before
    run._manifest['continuation']={'policy':'skip-all-started-v1','prior_manifest':prior['manifest'],
        'prior_report_sha256':hashlib.sha256(json.dumps(prior,sort_keys=True).encode()).hexdigest(),
        'carried_calls':len(run.calls),'carried_attempts':len(started),'carried_usage':prior['usage'],
        'carried_elapsed_seconds':prior['elapsed_seconds'],'note':'USD ceiling applies to carried plus new usage; no started attempt is retried.'}
    run._manifest.pop('fingerprint')
    run._manifest['fingerprint']=hashlib.sha256(json.dumps(run._manifest,sort_keys=True).encode()).hexdigest()
    run.emit('explicit_usd_extension',prior_fingerprint=fingerprint,prior_limit=old.run_estimated_usd_limit,
             combined_limit=config.run_estimated_usd_limit,skipped_started_attempts=len(started))
    for c in config.conditions:
        for role in ('repair','writer') if c.memory=='structured' else ('repair',):
            settings=getattr(c,role)
            run.agents[c.id,role]=(factory(settings,role,run.suite) if factory else LiveAgent(settings,role,run.suite)
                if config.live else ServiceDemo() if role=='repair' else ScriptedWriter())
    return run


def recovered(report):
    """Create a conservative view of an abandoned checkpoint; never mutate storage."""
    d=deepcopy(report)
    if d['state']=='running':
        d['state']='interrupted';d['stop_reason']='Recovered checkpoint; no execution resumed. Usage may be incomplete.'
        for c in d['calls']:
            if c['status']=='pending':c['status']='unknown'
        for row in d['attempts']:
            row['usage']=aggregate([c for c in d['calls'] if all(c[k]==row[k] for k in ('condition','repetition','job'))])
            if row['status']=='running':
                row['status']='success' if row['certified'] else 'interrupted'
                row['reason']=row['reason'] or 'Interrupted; only saved evidence is available.'
                row['usage']['usage_complete']=False
        d['usage']=aggregate(d['calls'])
        if d['manifest']['config']['live']:d['usage']['usage_complete']=False
    return d
