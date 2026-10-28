"""Validated, serializable experiment settings. Credentials never belong here."""
from dataclasses import asdict, dataclass, field
from copy import deepcopy

BAY_IDS = ('groundhog', 'notebook', 'structured')  # Stable bay identities, independent of policy.
POLICIES = ('groundhog', 'notebook', 'structured')
MODEL_EFFORTS = {
    'gpt-6-luna': ('default','none','low','medium','high','xhigh','max'),
    'gpt-6-sol': ('default','none','low','medium','high','xhigh','max'),
    'gpt-6-astra': ('default','low','medium','high','xhigh','max'),
}


def integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{label} must be an integer from {low} to {high}.')


@dataclass(frozen=True)
class MechanicConfig:
    bay_id: str
    name: str
    model: str = 'gpt-6-luna'
    reasoning: str = 'default'
    memory: str = 'groundhog'
    notebook_exchanges: int = 12
    memory_tokens: int = 1000
    step_limit: int = 12
    repair_output_tokens: int = 1024
    memory_output_tokens: int = 1600
    annotation: str = ''

    def validate(self):
        if self.bay_id not in BAY_IDS or self.memory not in POLICIES:
            raise ValueError('Unknown bay or memory policy.')
        if self.model not in MODEL_EFFORTS or self.reasoning not in MODEL_EFFORTS[self.model]:
            raise ValueError(f'Unsupported model/reasoning combination: {self.model}, {self.reasoning}.')
        if not isinstance(self.name,str) or not self.name.strip() or len(self.name)>60:
            raise ValueError('Mechanic name must contain 1–60 characters.')
        if not isinstance(self.annotation,str) or len(self.annotation)>4000:
            raise ValueError('Mechanic notes must be at most 4,000 characters.')
        for value,lo,hi,label in [(self.notebook_exchanges,0,100,'Notebook exchanges'),
              (self.memory_tokens,128,8000,'Memory token budget'),(self.step_limit,1,40,'Step limit'),
              (self.repair_output_tokens,128,4096,'Repair output limit'),
              (self.memory_output_tokens,128,4096,'Memory output limit')]:
            integer(value,lo,hi,label)
        return self


def default_mechanics():
    return tuple(MechanicConfig(bay_id=b,name=n,memory=b) for b,n in zip(BAY_IDS,
        ('Groundhog Day','Raw notebook','Four-level memory')))


@dataclass(frozen=True)
class ExperimentConfig:
    schema_version: int = 1
    name: str = 'Memory comparison'
    annotation: str = ''
    task_set: str = 'baseline-v1'
    jobs_per_bay: int = 3
    repetitions: int = 1
    live: bool = False
    max_total_tokens: int = 500000
    mechanics: tuple[MechanicConfig,...] = field(default_factory=default_mechanics)

    def validate(self):
        from .tasks import get_suite
        if self.schema_version != 1: raise ValueError('Unsupported configuration schema version.')
        suite=get_suite(self.task_set)
        integer(self.jobs_per_bay,1,len(suite.jobs),'Jobs per bay')
        integer(self.repetitions,1,10,'Repeated shifts')
        integer(self.max_total_tokens,1000,10000000,'Run token limit')
        if type(self.live) is not bool: raise ValueError('Run mode must be a boolean.')
        if not isinstance(self.name,str) or not self.name.strip() or len(self.name)>120:
            raise ValueError('Experiment name must contain 1–120 characters.')
        if not isinstance(self.annotation,str) or len(self.annotation)>8000:
            raise ValueError('Experiment notes must be at most 8,000 characters.')
        if tuple(m.bay_id for m in self.mechanics) != BAY_IDS:
            raise ValueError('Exactly three mechanics in stable bay order are required.')
        for m in self.mechanics: m.validate()
        return self

    def to_dict(self):
        data=asdict(self)
        data["mechanics"]=list(data["mechanics"])
        return data

    @classmethod
    def from_dict(cls, value):
        data=deepcopy(value)
        if not isinstance(data,dict): raise ValueError('Configuration must be an object.')
        try:
            data['mechanics']=tuple(MechanicConfig(**x) for x in data['mechanics'])
            return cls(**data).validate()
        except (KeyError,TypeError) as exc:
            raise ValueError('Configuration has missing or unknown fields.') from exc

    @property
    def attempts(self): return self.jobs_per_bay * len(self.mechanics) * self.repetitions
