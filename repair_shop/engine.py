"""One StateGraph per run, fresh thread per job, isolated cross-job stores."""
import os
# Never enable remote tracing implicitly from a parent shell.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
import json
import uuid
from datetime import datetime, timezone
from .costs import estimate, total_cost, PRICE_DATE, PRICE_URL, COST_NOTE
from copy import deepcopy
from typing import TypedDict
from threading import Event
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from .model import ModelError, OpenAIModel
from .config import ExperimentConfig, default_mechanics, MODEL_EFFORTS
from .tasks import get_suite
from dataclasses import replace

MODES = ("groundhog", "notebook", "structured")
LABELS = {"groundhog":"Groundhog Day", "notebook":"Raw notebook", "structured":"Four-level memory"}
EMPTY_NOTES = {"episodic":[], "semantic":[], "procedural":[]}

def note_tokens(notes):
    # An explicit, fixed serialization/tokenizer budget independent of API billing.
    import tiktoken
    return len(tiktoken.get_encoding("o200k_base").encode(json.dumps(notes, separators=(",",":"))))

def validate_notes(text, observed, budget=1000):
    notes = json.loads(text)
    if not isinstance(notes,dict) or set(notes) != set(EMPTY_NOTES):
        raise ValueError("wrong note sections")
    for kind, records in notes.items():
        if not isinstance(records,list):
            raise ValueError("notes must be lists")
        for r in records:
            if not isinstance(r,dict) or set(r) != {"model","revision","source_jobs","status","text"}:
                raise ValueError("invalid record")
            ids = r["source_jobs"]
            if not isinstance(ids,list) or not ids or any(type(i) is not int or i not in observed for i in ids):
                raise ValueError("invalid source jobs")
            if r["status"] not in ("tentative","test-supported","disputed") or not isinstance(r["text"],str):
                raise ValueError("invalid note status/text")
            for i in ids:
                if observed[i]["ticket"]["customer"] != f'{r["model"]} {r["revision"]}':
                    raise ValueError("cross-revision citation")
            if (kind == "procedural" or r["status"] == "test-supported") and not any(observed[i]["passed"] for i in ids):
                raise ValueError("unsupported success")
    if note_tokens(notes) > budget:
        raise ValueError("notes exceed configured token budget")
    return notes

class State(TypedDict, total=False):
    mode: str
    ticket: dict
    steps: int
    exchanges: list
    prior: object
    action: object
    done: bool
    passed: bool
    reason: str

class Run:
    def __init__(self, model=None, stop=None, cap=12, on_event=None, experiment=None, model_factory=None):
        if not 1 <= cap <= 40:
            raise ValueError("cap must be 1..40")
        note_tokens(EMPTY_NOTES)  # Resolve tokenizer before any paid calls.
        self.experiment=(experiment or ExperimentConfig(jobs_per_bay=10,live=bool(model and model.live),
            mechanics=tuple(replace(m,step_limit=cap,model=model.name if model and model.live and model.name in MODEL_EFFORTS else m.model) for m in default_mechanics()))).validate()
        self.suite=get_suite(self.experiment.task_set)
        self.settings={m.bay_id:m for m in self.experiment.mechanics}
        if model is not None:
            self.models={mode:model for mode in MODES}
        else:
            def factory(m):
                if not self.experiment.live: return self.suite.create_demo()
                return OpenAIModel(name=m.model,reasoning=m.reasoning,repair_output_tokens=m.repair_output_tokens,
                    memory_output_tokens=m.memory_output_tokens,memory_tokens=m.memory_tokens,
                    step_limit=m.step_limit,tools=list(self.suite.tools),task_instructions=self.suite.instructions)
            self.models={m.bay_id:(model_factory(m) if model_factory else factory(m)) for m in self.experiment.mechanics}
        self.model=self.models[MODES[0]]  # Compatibility for simple callers; runner uses models[bay].
        self.stop,self.cap=stop or Event(),cap
        self.repetition=1
        self.stop_reason=''
        self.config_reference=None
        self.id = uuid.uuid4().hex
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.selected_jobs = 0
        self.completed = False
        self.on_event = on_event
        self.on_checkpoint = None
        self.store,self.checkpointer = InMemoryStore(),InMemorySaver()
        self.events,self.results,self.calls = [],[],[]
        self.world = None
        self.error = None
        self.graph = self._graph()

    def namespace(self,mode):
        return (self.id,str(self.repetition),mode)

    def records(self,mode):
        item = self.store.get(self.namespace(mode),"records")
        return deepcopy(item.value) if item else {"history":[],"notes":deepcopy(EMPTY_NOTES),"observed":{}}

    def emit(self,kind,state,**extra):
        event = {"sequence":len(self.events)+1,"at":datetime.now(timezone.utc).isoformat(),"kind":kind,"mode":state["mode"],
                 "repetition":self.repetition,"step_limit":self.settings[state["mode"]].step_limit,
                 "memory_policy":self.settings[state["mode"]].memory,"model":self.models[state["mode"]].name,
                 "job":state["ticket"]["job"],"ticket":state["ticket"],"steps":state["steps"],**deepcopy(extra)}
        self.events.append(event)
        if self.on_event:
            self.on_event(deepcopy(event))

    def bill(self,reply,state,kind):
        self.calls.append({"mode":state["mode"],"job":state["ticket"]["job"],"kind":kind,
                           "input":reply.input_tokens,"output":reply.output_tokens,
                           "response_id":reply.request_id,"status":reply.status,"model":self.models[state["mode"]].name,
                           "repetition":self.repetition,
                           "cost_usd":estimate(self.models[state["mode"]].name,reply.input_tokens,reply.output_tokens,self.models[state["mode"]].live)})
        if self.on_checkpoint: self.on_checkpoint(self)
        if self.totals()['input']+self.totals()['output'] >= self.experiment.max_total_tokens:
            self.stop_reason='Run token limit reached; returned usage recorded.'
            self.stop.set()

    def totals(self, mode=None, job=None, repetition=None):
        calls=[x for x in self.calls if (mode is None or x["mode"]==mode) and (job is None or x["job"]==job) and (repetition is None or x["repetition"]==repetition)]
        return {"input":sum(x["input"] for x in calls),"output":sum(x["output"] for x in calls),
                "maintenance":sum(x["input"]+x["output"] for x in calls if x["kind"]=="memory"),"calls":len(calls),"cost_usd":total_cost(calls)}

    def _graph(self):
        def load(s):
            records=self.records(s["mode"])
            cfg=self.settings[s['mode']]
            prior = (records['history'][-cfg.notebook_exchanges:] if cfg.notebook_exchanges else []) if cfg.memory=='notebook' else records['notes'] if cfg.memory=='structured' else []
            self.emit("start",s,prior=prior)
            return {"prior":prior}
        def decide(s):
            if self.stop.is_set():
                return {"done":True,"reason":self.stop_reason or "stopped by user"}
            context={"ticket":s["ticket"],"steps_remaining":self.settings[s["mode"]].step_limit-s["steps"],
                     "prior_memory":s["prior"],"current_job_exchanges":s["exchanges"]}
            self.emit("thinking",s)
            if self.stop.is_set():
                return {"done":True,"reason":self.stop_reason or "stopped by user"}
            try:
                reply=self.models[s["mode"]].decide(deepcopy(context))
            except ModelError as e:
                self.error=str(e)
                self.stop.set()
                return {"done":True,"reason":self.error}
            self.bill(reply,s,"repair")
            if self.stop.is_set():
                return {"done":True,"reason":self.stop_reason or "stopped by user after in-flight request; returned usage recorded"}
            if reply.action is None:
                return {"done":True,"reason":"non-action or incomplete model response"}
            return {"action":reply.action}
        def execute(s):
            action=s["action"]
            result=self.world.call(action.get("name"),action.get("arguments",{}))
            steps=s["steps"]+1
            passed=self.world.passed
            exchange={"ticket":s["ticket"],"job_boundary":s["ticket"]["job"],
                      "action":deepcopy(action),"result":result}
            updated={"steps":steps,"exchanges":s["exchanges"]+[exchange],"passed":passed,
                     "done":passed or steps>=self.settings[s["mode"]].step_limit,
                     "reason":"passed test" if passed else "step cap reached" if steps>=self.settings[s["mode"]].step_limit else ""}
            self.emit("action",{**s,**updated},action=action,result=result,visible=self.world.snapshot())
            return updated
        def finish(s):
            self.emit("finish",s,passed=s["passed"],reason=s["reason"])
            return {}
        def save(s):
            records=self.records(s["mode"])
            job=s["ticket"]["job"]
            warning=""
            cfg=self.settings[s['mode']]
            if cfg.memory=='notebook':
                records['history']=(records['history']+deepcopy(s['exchanges']))[-cfg.notebook_exchanges:] if cfg.notebook_exchanges else []
            if cfg.memory=='structured':
                records["observed"][job]={"ticket":s["ticket"],"passed":s["passed"]}
                if not self.stop.is_set():
                    self.emit("maintenance_start",s)
                    if self.stop.is_set():
                        warning="Memory write skipped after stop."
                    else:
                        try:
                            reply=self.models[s["mode"]].maintain({"ticket":s["ticket"],"passed":s["passed"],
                                "exchanges":deepcopy(s["exchanges"]),"previous_notes":deepcopy(records["notes"])})
                            self.bill(reply,s,"memory")
                            if reply.status != "completed":
                                raise ValueError("incomplete maintenance output")
                            records["notes"]=validate_notes(reply.text,records["observed"],cfg.memory_tokens)
                        except (ValueError,TypeError,KeyError) as exc:
                            validation_reason=str(exc) if type(exc) is ValueError else type(exc).__name__
                            self.emit("memory_rejected",s,validation_reason=validation_reason)
                            warning="Memory update rejected; previous validated notes retained. No retry."
                        except ModelError as e:
                            self.error=str(e)
                            self.stop.set()
                            warning=self.error
            # No mode stores private scoring/replay data for another mode.
            if cfg.memory!="groundhog":
                self.store.put(self.namespace(s["mode"]),"records",records)
            self.emit("memory",s,notes=records["notes"] if cfg.memory=="structured" else records["history"] if cfg.memory=="notebook" else [],warning=warning)
            self.results.append({"mode":s["mode"],"model":self.models[s["mode"]].name,"repetition":self.repetition,
                                 "memory_policy":cfg.memory,"reasoning":cfg.reasoning,"step_limit":cfg.step_limit,"job":job,"passed":s["passed"],"steps":s["steps"],
                                 "reason":s["reason"],"warning":warning,**self.totals(s["mode"],job,self.repetition),
                                 "task_metrics":self.world.metrics() if hasattr(self.world,"metrics") else {}})
            self.emit("invoice",s,usage=self.totals(s["mode"],job,self.repetition),passed=s["passed"],live=self.models[s["mode"]].live)
            return {}
        builder=StateGraph(State)
        for name,node in [("load",load),("decide",decide),("execute",execute),("finish",finish),("save",save)]:
            builder.add_node(name,node)
        builder.add_edge(START,"load")
        builder.add_edge("load","decide")
        builder.add_conditional_edges("decide",lambda s:"finish" if s["done"] else "execute")
        builder.add_conditional_edges("execute",lambda s:"finish" if s["done"] else "decide")
        builder.add_edge("finish","save")
        builder.add_edge("save",END)
        return builder.compile(checkpointer=self.checkpointer,store=self.store)

    def job(self, mode, job):
        if mode not in MODES:
            raise ValueError("unknown mode")
        self.world=self.suite.create_world(job)
        state={"mode":mode,"ticket":job.ticket(),"steps":0,"exchanges":[],"done":False,"passed":False,"reason":""}
        config={"configurable":{"thread_id":f"{self.id}:{self.repetition}:{mode}:{job.number}"},"recursion_limit":2*self.settings[mode].step_limit+10}
        yield from self.graph.stream(state,config,stream_mode="updates")

    def run(self, jobs=None):
        if jobs is not None:
            jobs=tuple(jobs)
            self.experiment=replace(self.experiment,jobs_per_bay=len(jobs)).validate()
        else:
            jobs=self.suite.jobs[:self.experiment.jobs_per_bay]
        self.selected_jobs = len(jobs)
        for repetition in range(1,self.experiment.repetitions+1):
            self.repetition=repetition
            for job in jobs:
                for mode in MODES:
                    if self.stop.is_set(): return
                    yield from self.job(mode,job)
        self.completed = not self.stop.is_set() and self.error is None

    def report(self):
        return {"schema_version":2,"run_id":self.id,"seed":self.suite.seed,
                "task_set":self.suite.id,"task_fingerprint":self.suite.fingerprint,
                "model":self.model.name,"live":self.experiment.live,
                "configuration":self.experiment.to_dict(),"config_reference":self.config_reference,
                "started_at":self.started_at,"selected_jobs":self.selected_jobs,
                "completed":self.completed,"stop_reason":self.stop_reason,
                "pricing":{"date":PRICE_DATE,"source":PRICE_URL,"note":COST_NOTE},
                "cap":self.cap,"results":deepcopy(self.results),"usage":self.totals(),"error":self.error,
                "usage_complete":self.error is None,"events":deepcopy(self.events),"calls":deepcopy(self.calls)}
