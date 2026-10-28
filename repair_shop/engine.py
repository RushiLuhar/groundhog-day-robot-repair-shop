"""One StateGraph per run, fresh thread per job, isolated cross-job stores."""
import os
# Never enable remote tracing implicitly from a parent shell.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
import json
import uuid
from copy import deepcopy
from typing import TypedDict
from threading import Event
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from .world import World, JOBS, SEED
from .model import ModelError

MODES = ("groundhog", "notebook", "structured")
LABELS = {"groundhog":"Groundhog Day", "notebook":"Raw notebook", "structured":"Four-level memory"}
EMPTY_NOTES = {"episodic":[], "semantic":[], "procedural":[]}

def note_tokens(notes):
    # An explicit, fixed serialization/tokenizer budget independent of API billing.
    import tiktoken
    return len(tiktoken.get_encoding("o200k_base").encode(json.dumps(notes, separators=(",",":"))))

def validate_notes(text, observed):
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
    if note_tokens(notes) > 1000:
        raise ValueError("notes exceed 1000-token budget")
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
    def __init__(self, model, stop=None, cap=12):
        if not 1 <= cap <= 12:
            raise ValueError("cap must be 1..12")
        note_tokens(EMPTY_NOTES)  # Resolve tokenizer before any paid calls.
        self.model,self.stop,self.cap = model,stop or Event(),cap
        self.id = uuid.uuid4().hex
        self.store,self.checkpointer = InMemoryStore(),InMemorySaver()
        self.events,self.results,self.calls = [],[],[]
        self.world = None
        self.error = None
        self.graph = self._graph()

    def namespace(self,mode):
        return (self.id,mode)

    def records(self,mode):
        item = self.store.get(self.namespace(mode),"records")
        return deepcopy(item.value) if item else {"history":[],"notes":deepcopy(EMPTY_NOTES),"observed":{}}

    def emit(self,kind,state,**extra):
        event = {"sequence":len(self.events)+1,"kind":kind,"mode":state["mode"],
                 "job":state["ticket"]["job"],"ticket":state["ticket"],"steps":state["steps"],**deepcopy(extra)}
        self.events.append(event)

    def bill(self,reply,state,kind):
        self.calls.append({"mode":state["mode"],"job":state["ticket"]["job"],"kind":kind,
                           "input":reply.input_tokens,"output":reply.output_tokens,
                           "response_id":reply.request_id,"status":reply.status})

    def totals(self, mode=None, job=None):
        calls=[x for x in self.calls if (mode is None or x["mode"]==mode) and (job is None or x["job"]==job)]
        return {"input":sum(x["input"] for x in calls),"output":sum(x["output"] for x in calls),
                "maintenance":sum(x["input"]+x["output"] for x in calls if x["kind"]=="memory"),"calls":len(calls)}

    def _graph(self):
        def load(s):
            records=self.records(s["mode"])
            prior = records["history"][-12:] if s["mode"]=="notebook" else records["notes"] if s["mode"]=="structured" else []
            self.emit("start",s,prior=prior)
            return {"prior":prior}
        def decide(s):
            if self.stop.is_set():
                return {"done":True,"reason":"stopped by user"}
            context={"ticket":s["ticket"],"steps_remaining":self.cap-s["steps"],
                     "prior_memory":s["prior"],"current_job_exchanges":s["exchanges"]}
            self.emit("thinking",s)
            try:
                reply=self.model.decide(deepcopy(context))
            except ModelError as e:
                self.error=str(e)
                self.stop.set()
                return {"done":True,"reason":self.error}
            self.bill(reply,s,"repair")
            if self.stop.is_set():
                return {"done":True,"reason":"stopped by user after in-flight request; returned usage recorded"}
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
                     "done":passed or steps>=self.cap,
                     "reason":"passed test" if passed else "step cap reached" if steps>=self.cap else ""}
            self.emit("action",{**s,**updated},action=action,result=result,visible=self.world.snapshot())
            return updated
        def finish(s):
            self.emit("finish",s,passed=s["passed"],reason=s["reason"])
            return {}
        def save(s):
            records=self.records(s["mode"])
            job=s["ticket"]["job"]
            warning=""
            if s["mode"]=="notebook":
                records["history"]=(records["history"]+deepcopy(s["exchanges"]))[-12:]
            if s["mode"]=="structured":
                records["observed"][job]={"ticket":s["ticket"],"passed":s["passed"]}
                if not self.stop.is_set():
                    try:
                        reply=self.model.maintain({"ticket":s["ticket"],"passed":s["passed"],
                            "exchanges":deepcopy(s["exchanges"]),"previous_notes":deepcopy(records["notes"])})
                        self.bill(reply,s,"memory")
                        if reply.status != "completed":
                            raise ValueError("incomplete maintenance output")
                        records["notes"]=validate_notes(reply.text,records["observed"])
                    except (ValueError,TypeError,KeyError):
                        warning="Memory update rejected; previous validated notes retained. No retry."
                    except ModelError as e:
                        self.error=str(e)
                        self.stop.set()
                        warning=self.error
            # No mode stores private scoring/replay data for another mode.
            if s["mode"]!="groundhog":
                self.store.put(self.namespace(s["mode"]),"records",records)
            self.emit("memory",s,notes=records["notes"] if s["mode"]=="structured" else records["history"] if s["mode"]=="notebook" else [],warning=warning)
            self.results.append({"mode":s["mode"],"job":job,"passed":s["passed"],"steps":s["steps"],
                                 "reason":s["reason"],"warning":warning,**self.totals(s["mode"],job)})
            self.emit("invoice",s,usage=self.totals(s["mode"],job),passed=s["passed"],live=self.model.live)
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
        self.world=World(job)
        state={"mode":mode,"ticket":job.ticket(),"steps":0,"exchanges":[],"done":False,"passed":False,"reason":""}
        config={"configurable":{"thread_id":f"{self.id}:{mode}:{job.number}"},"recursion_limit":60}
        yield from self.graph.stream(state,config,stream_mode="updates")

    def run(self, jobs=JOBS):
        for job in jobs:
            for mode in MODES:
                if self.stop.is_set():
                    return
                yield from self.job(mode,job)

    def report(self):
        return {"run_id":self.id,"seed":SEED,"model":self.model.name,"live":self.model.live,
                "cap":self.cap,"results":self.results,"usage":self.totals(),"error":self.error,
                "usage_complete":self.error is None,"events":self.events,"calls":self.calls}
