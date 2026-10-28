"""Versioned memory validation, deterministic retention and auditable provenance."""
import json
from copy import deepcopy
import hashlib

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


def source_jobs(prior):
    if isinstance(prior,list):return sorted({x['ticket']['job'] for x in prior})
    return sorted({i for records in prior.values() for r in records for i in r['source_jobs']})


def record_id(kind,record):
    return hashlib.sha256(json.dumps([kind,record],sort_keys=True).encode()).hexdigest()[:12]


def merge_notes(text,previous,observed,budget):
    """Validate candidates separately; omission never silently erases older records.

    Budget eviction retains the newest evidence first, with procedural/semantic notes
    ahead of episodes for equal source age. It never consults future tasks or scoring.
    """
    incoming=json.loads(text)
    if not isinstance(incoming,dict) or set(incoming)!=set(EMPTY_NOTES):raise ValueError('wrong note sections')
    if any(not isinstance(v,list) for v in incoming.values()):raise ValueError('notes must be lists')
    candidates=[];rejected=[]
    for kind,records in previous.items():
        candidates.extend((kind,deepcopy(r)) for r in records)
    accepted=[]
    for kind,records in incoming.items():
        for index,r in enumerate(records):
            try:
                # Per-record validation prevents a single bad citation discarding valid siblings.
                validate_notes(json.dumps({**EMPTY_NOTES,kind:[r]}),observed,budget)
            except (ValueError,TypeError,KeyError) as exc:
                rejected.append({'section':kind,'index':index,'reason':str(exc) if type(exc) is ValueError else type(exc).__name__})
                continue
            candidates.append((kind,deepcopy(r)));accepted.append(record_id(kind,r))
    # Same statement can acquire a newer citation; keep only its latest valid form.
    distinct={}
    for kind,r in candidates:
        key=(kind,r['model'],r['revision'],r['status'],r['text'])
        if key not in distinct or max(r['source_jobs'])>=max(distinct[key][1]['source_jobs']):distinct[key]=(kind,r)
    priority={'procedural':0,'semantic':1,'episodic':2}
    ordered=sorted(distinct.values(),key=lambda x:(-max(x[1]['source_jobs']),priority[x[0]],record_id(*x)))
    notes=deepcopy(EMPTY_NOTES);evicted=[]
    for kind,r in ordered:
        trial=deepcopy(notes);trial[kind].append(r)
        if note_tokens(trial)<=budget:notes=trial
        else:evicted.append(record_id(kind,r))
    retained=[record_id(k,r) for k,rs in notes.items() for r in rs]
    old=[record_id(k,r) for k,rs in previous.items() for r in rs]
    return notes,{'policy':'merge_v2','accepted_record_ids':accepted,'rejected_records':rejected,
        'evicted_record_ids':evicted,'removed_prior_record_ids':sorted(set(old)-set(retained)),
        'retained_record_ids':retained,'retained_source_jobs':source_jobs(notes),'note_tokens':note_tokens(notes),
        'budget_tokens':budget}


def memory_audit(prior,ticket,earlier_jobs):
    """Metadata only: supplied evidence is not proof the model used it correctly."""
    supplied=source_jobs(prior)
    matching=[j['job'] for j in earlier_jobs if j['customer']==ticket['customer']]
    return {'supplied_record_ids':[record_id(k,r) for k,rs in prior.items() for r in rs] if isinstance(prior,dict) else [],
            'matching_previous_jobs':matching,'supplied_source_jobs':supplied,
            'matching_jobs_supplied':sorted(set(matching)&set(supplied)),
            'matching_jobs_missing':sorted(set(matching)-set(supplied)),
            'note':'Matching means same family/revision, not guaranteed relevance or use. A missing older citation may be superseded by a newer note.'}
