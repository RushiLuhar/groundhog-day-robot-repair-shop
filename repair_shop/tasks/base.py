"""Task interface v1. Keep private scoring state out of observations and prompts."""
from dataclasses import dataclass
from typing import Protocol, Callable
import hashlib
import json


class TaskTicket(Protocol):
    number: int
    def ticket(self) -> dict: ...


class TaskWorld(Protocol):
    passed: bool
    def call(self, name: str, arguments: dict) -> dict: ...
    def snapshot(self) -> dict: ...  # Public observations only.


@dataclass(frozen=True)
class TaskSuite:
    id: str
    title: str
    description: str
    seed: str
    jobs: tuple[TaskTicket,...]
    tools: tuple[dict,...]
    instructions: str
    create_world: Callable[[TaskTicket], TaskWorld]
    create_demo: Callable
    fixture_data: dict
    implementation_version: str = '1'

    @property
    def fingerprint(self):
        # Semantic code changes must bump implementation_version and suite id.
        payload={'id':self.id,'seed':self.seed,'implementation_version':self.implementation_version,
                 'fixtures':self.fixture_data,'tools':self.tools,'instructions':self.instructions}
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def public_description(self):
        return {'id':self.id,'title':self.title,'description':self.description,'seed':self.seed,
                'fingerprint':self.fingerprint,'jobs':[j.ticket() for j in self.jobs]}
