import json
from copy import deepcopy
from threading import Event
import pytest
from repair_shop.engine import Run, MODES, validate_notes, EMPTY_NOTES
from repair_shop.model import DemoModel, Reply, ModelError
from repair_shop.world import JOBS

class Spy(DemoModel):
    def __init__(self): self.contexts=[]
    def decide(self,c):
        self.contexts.append(deepcopy(c))
        r=super().decide(c); r.input_tokens=7; r.output_tokens=3; return r
    def maintain(self,p):
        r=super().maintain(p); r.input_tokens=11; r.output_tokens=5; return r

def test_full_mock_shift_isolated_and_accounted():
    m=Spy(); r=Run(m); list(r.run())
    assert len(r.results)==30 and all(x['passed'] for x in r.results)
    assert all(x['steps']<=12 for x in r.results)
    assert r.totals()['maintenance']==160
    assert r.totals()['input']+r.totals()['output']==sum(x['steps']*10 for x in r.results)+160
    assert r.records('groundhog')['history']==[]
    assert len(r.records('notebook')['history'])==12
    assert r.records('structured')['notes']['episodic']
    assert not Run(m).records('structured')['notes']['episodic']

def test_raw_notebook_is_exact_fixed_window_with_tickets():
    m=Spy(); r=Run(m)
    for j in JOBS[:3]: list(r.job('notebook',j))
    starts=[e for e in r.events if e['kind']=='start']
    actions=[{'ticket':e['ticket'],'job_boundary':e['job'],'action':e['action'],'result':e['result']} for e in r.events if e['kind']=='action' and e['job']<3]
    assert starts[2]['prior']==actions[-12:]
    contexts=[c for c in m.contexts if c['ticket']['job']==3]
    assert all(c['prior_memory']==actions[-12:] for c in contexts)
    assert contexts[0]['current_job_exchanges']==[]

def test_cap_nonaction_and_stop():
    class Inspect(DemoModel):
        def decide(self,c): return Reply({'name':'inspect','arguments':{}})
    r=Run(Inspect()); list(r.job('groundhog',JOBS[0]))
    assert r.results[0]['steps']==12 and not r.results[0]['passed']
    class Quit(DemoModel):
        def decide(self,c): return Reply(None,2,3)
    r=Run(Quit()); list(r.job('groundhog',JOBS[0]))
    assert r.results[0]['steps']==0 and not r.results[0]['passed'] and r.totals()['output']==3
    stop=Event(); stop.set(); r=Run(Inspect(),stop); list(r.run()); assert not r.calls

def test_api_error_stops_no_retry():
    class Broken(DemoModel):
        def decide(self,c): raise ModelError('request uncertain')
    r=Run(Broken()); list(r.run()); assert r.error and len(r.results)==1 and not r.report()['usage_complete']

def test_invalid_memory_retains_previous_and_counts_call():
    class Invalid(Spy):
        def maintain(self,p): return Reply(None,11,5,text='not json')
    r=Run(Invalid()); list(r.job('structured',JOBS[0]))
    assert r.results[0]['warning'] and r.totals()['maintenance']==16
    assert r.records('structured')['notes']==EMPTY_NOTES

def test_note_validation_rejects_hidden_future_and_false_success():
    record={'model':'Amber','revision':'R1','source_jobs':[1],'status':'test-supported','text':'recipe'}
    notes={**EMPTY_NOTES,'procedural':[record]}
    with pytest.raises(ValueError): validate_notes(json.dumps(notes),{})
    with pytest.raises(ValueError): validate_notes(json.dumps(notes),{1:{'ticket':JOBS[0].ticket(),'passed':False}})

def test_valid_notes_preserve_distinct_revisions_and_cap():
    records=[]
    for job in (JOBS[0],JOBS[8]):
        records.append({'model':job.family,'revision':job.revision,'source_jobs':[job.number],
                        'status':'test-supported','text':'Only an observed supported repair sequence.'})
    observed={j.number:{'ticket':j.ticket(),'passed':True} for j in (JOBS[0],JOBS[8])}
    notes={k:deepcopy(records) for k in EMPTY_NOTES}
    assert validate_notes(json.dumps(notes),observed)==notes
    notes['semantic'][0]['text']='very long observation ' * 1500
    with pytest.raises(ValueError): validate_notes(json.dumps(notes),observed)

def test_structured_notes_enter_next_job_with_fresh_transcript():
    model=Spy(); run=Run(model)
    list(run.job('structured',JOBS[0]))
    saved=deepcopy(run.records('structured')['notes'])
    assert saved['episodic']
    list(run.job('structured',JOBS[1]))
    first=next(c for c in model.contexts if c['ticket']['job']==2)
    assert first['prior_memory']==saved
    assert first['current_job_exchanges']==[]
    assert run.totals()['maintenance']==32
