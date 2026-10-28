"""Deterministic fictional repair world. Hidden recipes never enter job tickets."""
from dataclasses import dataclass, field
from copy import deepcopy

SEED = "repair-world-v1:20261028"
OPERATIONS = ("vent", "tune", "seal", "reseat_cable", "replace_fuse")

@dataclass(frozen=True)
class Job:
    number: int
    family: str
    revision: str = "R1"
    cooler: bool = True
    cable: bool = False
    fuse: bool = False
    progress: tuple[str, ...] = ()

    def ticket(self):
        return {"job": self.number, "customer": f"{self.family} {self.revision}",
                "complaint": "no startup" if self.fuse else "stuttering"}

JOBS = (
    Job(1,"Amber"), Job(2,"Mint"), Job(3,"Amber"),
    Job(4,"Amber",progress=("vent",)), Job(5,"Mint",cooler=False,cable=True),
    Job(6,"Mint",cooler=False,fuse=True), Job(7,"Amber",cable=True),
    Job(8,"Mint"), Job(9,"Amber","R2"), Job(10,"Amber","R2",progress=("tune",)),
)

@dataclass
class World:
    job: Job
    progress: list[str] = field(default_factory=list)
    cable_fixed: bool = False
    fuse_fixed: bool = False
    passed: bool = False

    def __post_init__(self):
        self.progress = list(self.job.progress)

    @property
    def recipe(self):
        return ("vent", "tune", "seal") if (self.job.family,self.job.revision)==("Amber","R1") else ("tune","vent","seal")

    def inspect(self):
        return {"model": self.job.family, "revision": self.job.revision,
                "cooler": "unstable" if self.job.cooler and "seal" not in self.progress else "normal",
                "cable": "loose" if self.job.cable and not self.cable_fixed else "secure",
                "fuse": "blown" if self.job.fuse and not self.fuse_fixed else "intact",
                "visible_progress": list(self.progress)}

    def call(self, name, arguments):
        if name == "inspect" and arguments == {}:
            return self.inspect()
        if name == "test" and arguments == {}:
            readings = self.inspect()
            failures = [k for k in ("cooler","cable","fuse") if readings[k] in ("unstable","loose","blown")]
            self.passed = not failures
            return {"pass": self.passed, "faults_observed": failures}
        if name != "operate" or set(arguments) != {"operation"} or arguments["operation"] not in OPERATIONS:
            return {"ok": False, "reason": "invalid tool or arguments"}
        op = arguments["operation"]
        if op == "reseat_cable":
            self.cable_fixed = True
        elif op == "replace_fuse":
            self.fuse_fixed = True
        elif not self.job.cooler:
            return {"ok": False, "reason": "cooler readings are normal; inspect other components"}
        elif op in self.progress:
            return {"ok": False, "reason": "operation already completed", "operation": op}
        else:
            expected = self.recipe[len(self.progress)]
            if op != expected:
                return {"ok": False, "reason": f"{op} blocked; {expected} must be completed first"}
            self.progress.append(op)
        return {"ok": True, "operation": op, "visible_progress": list(self.progress)}

    def snapshot(self):
        return deepcopy(self.inspect())
