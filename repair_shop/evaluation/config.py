"""Immutable conditions with independent repair and job-end writer settings."""
from dataclasses import dataclass, field, asdict, replace
from copy import deepcopy
import math
from ..config import MODEL_EFFORTS, integer
from ..costs import RATES

REPAIR_PROMPT='repair-objective-v1'
WRITER_PROMPT='job-end-writer-v1'
LOG_VERSION='literal-observation-en-v1'
MEMORY_VERSION='typed-record-merge-v1'

@dataclass(frozen=True)
class AgentConfig:
    model: str='gpt-6-luna'
    reasoning: str='default'
    prompt_version: str=REPAIR_PROMPT
    response_output_cap: int=2048

    def validate(self,role):
        if self.model not in MODEL_EFFORTS or self.reasoning not in MODEL_EFFORTS[self.model]:
            raise ValueError(f'Unsupported {role} model/reasoning combination.')
        expected=REPAIR_PROMPT if role=='repair' else WRITER_PROMPT
        if self.prompt_version!=expected: raise ValueError(f'Unsupported {role} prompt version.')
        integer(self.response_output_cap,128,4096,f'{role} response output cap')
        return self

@dataclass(frozen=True)
class Condition:
    id: str
    memory: str='none'
    repair: AgentConfig=field(default_factory=AgentConfig)
    writer: AgentConfig=field(default_factory=lambda:AgentConfig(prompt_version=WRITER_PROMPT))
    rolling_entry_limit: int=40
    retention_tokens: int=3000
    supply_tokens: int=2000
    tool_step_limit: int=20
    job_total_token_allowance: int=30000

    def validate(self):
        import re
        if not isinstance(self.id,str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,39}',self.id):
            raise ValueError('Condition ID must be a short unique lowercase identifier.')
        if self.memory not in ('none','rolling','structured'):raise ValueError('Unknown memory policy.')
        self.repair.validate('repair');self.writer.validate('writer')
        for key,lo,hi in [('rolling_entry_limit',0,200),('retention_tokens',128,16000),
                         ('supply_tokens',128,16000),('tool_step_limit',1,40),('job_total_token_allowance',128,1000000)]:
            integer(getattr(self,key),lo,hi,key)
        return self


def default_conditions():
    return tuple(Condition(p,p) for p in ('none','rolling','structured'))

@dataclass(frozen=True)
class EvaluationConfig:
    schema_version: int=2
    name: str='Eight-ticket memory comparison'
    task_set: str='service-v1'
    variant: str='standard-v1'
    jobs: int=8
    repetitions: int=1
    live: bool=False
    run_total_token_limit: int=500000
    run_estimated_usd_limit: float | None=0.25
    request_admission_policy: str='returned-usage-v1'
    conditions: tuple[Condition,...]=field(default_factory=default_conditions)

    def validate(self):
        if self.schema_version!=2:raise ValueError('Use the legacy workshop for schema-v1 experiments; no implicit migration.')
        if not isinstance(self.name,str) or not self.name.strip() or len(self.name)>120:raise ValueError('Invalid experiment name.')
        if self.task_set!='service-v1' or self.variant!='standard-v1':raise ValueError('Unknown task set or variant.')
        integer(self.jobs,1,8,'jobs');integer(self.repetitions,1,10,'repetitions')
        integer(self.run_total_token_limit,128,10000000,'run total token limit')
        if self.request_admission_policy not in ('returned-usage-v1','conservative-bytes-v1'):
            raise ValueError('Unknown request admission policy.')
        if type(self.live) is not bool:raise ValueError('live must be a boolean.')
        if not isinstance(self.conditions,tuple) or not len(self.conditions)>=1:raise ValueError('Choose a nonempty condition list.')
        for c in self.conditions:c.validate()
        if len({c.id for c in self.conditions})!=len(self.conditions):raise ValueError('Condition IDs must be unique.')
        cap=self.run_estimated_usd_limit
        if cap is not None and (type(cap) not in (int,float) or not math.isfinite(cap) or cap<=0):raise ValueError('USD limit must be positive or null.')
        if self.live and cap is not None:
            models={a.model for c in self.conditions for a in ([c.repair,c.writer] if c.memory=='structured' else [c.repair])}
            if models-set(RATES):raise ValueError('USD guard requires known prices for every active model; choose a priced model or explicitly use null with the token guard.')
        return self

    def to_dict(self):return asdict(self)

    @classmethod
    def from_dict(cls,value):
        d=deepcopy(value)
        try:
            if d.get('schema_version')!=2:raise ValueError('Legacy configurations remain in the legacy workshop; no automatic conversion.')
            d['conditions']=tuple(Condition(**{**c,'repair':AgentConfig(**c['repair']),'writer':AgentConfig(**c['writer'])}) for c in d['conditions'])
            return cls(**d).validate()
        except (TypeError,KeyError,AttributeError) as e:raise ValueError('Invalid or unknown configuration fields.') from e

    @property
    def attempts(self):return self.jobs*self.repetitions*len(self.conditions)


def preset(name='memory'):
    c=EvaluationConfig()
    if name=='reasoning':return replace(c,name='Paired reasoning comparison',conditions=tuple(
        Condition(e,'structured',repair=replace(AgentConfig(),reasoning=e)) for e in ('low','high')))
    if name=='model':return replace(c,name='Paired model comparison',run_estimated_usd_limit=None,conditions=(
        Condition('luna','structured'),Condition('sol','structured',repair=replace(AgentConfig(),model='gpt-6-sol'))))
    if name=='budget':return replace(c,name='Paired output-budget comparison',conditions=(
        Condition('cap-1024','structured',repair=replace(AgentConfig(),response_output_cap=1024)),Condition('cap-2048','structured')))
    if name!='memory':raise ValueError('Unknown preset.')
    return c
