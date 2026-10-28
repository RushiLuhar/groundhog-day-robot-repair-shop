"""Sequential paired-condition execution with explicit request/attempt accounting."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from threading import Event
import hashlib,json,subprocess,time,uuid
from ..tasks import get_evaluation_suite
from ..costs import estimate,total_cost,PRICE_DATE,PRICE_URL,COST_NOTE
from .config import EvaluationConfig,LOG_VERSION,MEMORY_VERSION
from .models import LiveAgent,ScriptedWriter,PROMPTS
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
        self._started=None;self.elapsed_seconds=0
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
            'pricing':{'date':PRICE_DATE,'url':PRICE_URL,'note':COST_NOTE},
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
                        'memory_supply_audit':{},'memory_update_audit':{},'memory_after':[]})
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
        call={k:row[k] for k in ('condition','repetition','job')}
        call.update(role=role,model=settings.model,status='pending',input=None,output=None,cost_usd=None,
                    response_status='',end_reason='')
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
                    response_status=reply.status,end_reason=reply.end_reason,elapsed_seconds=time.monotonic()-start)
        self.save()
        user_stopped=self.stop.is_set() and not self.stop_reason
        self.budget_reason(c,row)
        return reply,'Stopped by user after returned usage.' if user_stopped else ''
    def run(self):
        if self.state!='ready':raise ValueError('A run cannot be resumed or executed twice.')
        self.state='running';self._started=time.monotonic()
        try:
            for row in self.attempts:
                if self.stop.is_set():break
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
                            'prior_memory':deepcopy(prior)}
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
            self.elapsed_seconds=time.monotonic()-self._started
            try:self.save()
            except Exception:self.persistence_error='Final checkpoint failed; export the in-memory report.'
    def report(self):
        rows=deepcopy(self.attempts)
        for r in rows:r['usage']=self.totals(r)
        return {'schema_version':2,'run_id':self.id,'started_at':self.started_at,'state':self.state,
            'manifest':self.manifest,'attempts':rows,'calls':deepcopy(self.calls),'events':deepcopy(self.events),
            'usage':self.totals(),'error':self.error,'stop_reason':self.stop_reason,
            'elapsed_seconds':time.monotonic()-self._started if self.state=='running' and self._started else self.elapsed_seconds,
            'persistence_error':self.persistence_error,'export_error':self.export_error}


def recovered(report):
    """Create a conservative view of an abandoned checkpoint; never mutate storage."""
    d=deepcopy(report)
    if d['state']=='running':
        d['state']='interrupted';d['stop_reason']='Recovered checkpoint; no execution resumed. Usage may be incomplete.'
        for c in d['calls']:
            if c['status']=='pending':c['status']='unknown'
        for row in d['attempts']:
            if row['status']=='running':
                row['status']='success' if row['certified'] else 'interrupted'
                row['reason']=row['reason'] or 'Interrupted; only saved evidence is available.'
                row['usage']['usage_complete']=False
        d['usage']=aggregate(d['calls'])
        if d['manifest']['config']['live']:d['usage']['usage_complete']=False
    return d
