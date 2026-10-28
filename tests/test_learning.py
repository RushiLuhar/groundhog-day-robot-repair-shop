import json
from copy import deepcopy
from dataclasses import replace
import pytest
from repair_shop.config import ExperimentConfig
from repair_shop.engine import Run
from repair_shop.memory import EMPTY_NOTES,merge_notes,note_tokens
from repair_shop.tasks import get_suite
from repair_shop.tasks.learning import LearningWorld,JOBS


def record(job=1,family='Amber',revision='R1',text='Observed calibration',status='test-supported'):
    return {'model':family,'revision':revision,'source_jobs':[job],'text':text,'status':status}


def test_merge_preserves_omitted_notes_and_valid_siblings():
    previous={**deepcopy(EMPTY_NOTES),'procedural':[record()]}
    observed={1:{'ticket':{'customer':'Amber R1'},'passed':True},2:{'ticket':{'customer':'Mint R1'},'passed':True}}
    incoming={**deepcopy(EMPTY_NOTES),'procedural':[record(2,'Mint'),record(99)]}
    notes,audit=merge_notes(json.dumps(incoming),previous,observed,1000)
    assert sorted(r['source_jobs'][0] for r in notes['procedural'])==[1,2]
    assert len(audit['rejected_records'])==1 and audit['rejected_records'][0]['reason']=='invalid source jobs'
    assert audit['removed_prior_record_ids']==[]
    unchanged,_=merge_notes(json.dumps(EMPTY_NOTES),notes,observed,1000)
    assert unchanged==notes


def test_budget_eviction_deterministic_and_reported():
    obs={i:{'ticket':{'customer':'Amber R1'},'passed':True} for i in range(1,10)}
    candidates={**deepcopy(EMPTY_NOTES),'semantic':[record(i,text=('Evidence %s '%i)*8) for i in obs]}
    a,report=merge_notes(json.dumps(candidates),EMPTY_NOTES,obs,128)
    b,again=merge_notes(json.dumps(candidates),EMPTY_NOTES,obs,128)
    assert a==b and report==again and report['evicted_record_ids'] and note_tokens(a)<=128
    assert 9 in report['retained_source_jobs']


def test_old_configs_keep_legacy_policy():
    data=ExperimentConfig().to_dict()
    for m in data['mechanics']:m.pop('memory_update_policy')
    assert all(m.memory_update_policy=='replace_v1' for m in ExperimentConfig.from_dict(data).mechanics)
    assert all(m.memory_update_policy=='merge_v2' for m in ExperimentConfig().mechanics)


def test_learning_observations_do_not_leak_targets_or_phase():
    w=LearningWorld(JOBS[0]);public=w.call('inspect',{})
    assert 'target' not in public and 'phase' not in public
    assert public['calibration']=={'x':0,'y':0,'z':0}
    assert w.call('measure',{'axis':'x'})=={'axis':'x','current':0,'signed_error':-2}
    assert not w.call('apply_calibration',{'x':2,'y':7,'z':4})['ok']
    w.call('power',{'state':'off'});w.call('apply_calibration',{'x':2,'y':7,'z':4})
    assert not w.call('test',{})['pass']
    w.call('power',{'state':'on'});assert w.call('test',{})['pass']
    exception=LearningWorld(JOBS[14]);assert 'replacement' in exception.inspect()['module_marking']
    exception.call('power',{'state':'off'});exception.call('apply_calibration',{'x':4,'y':9,'z':2});exception.call('power',{'state':'on'})
    assert not exception.call('test',{})['pass']


def test_full_sequence_reuse_exceptions_controls_and_reset():
    c=ExperimentConfig(task_set='learning-v1',jobs_per_bay=32,repetitions=2)
    r=Run(experiment=c);list(r.run())
    assert len(r.results)==192 and all(x['passed'] for x in r.results)
    assert max(x['steps'] for x in r.results)<=12
    results={(x['repetition'],x['mode'],x['job']):x for x in r.results}
    # Scripted demonstration proves an opportunity exists, not that a live model exploits it.
    assert results[1,'structured',4]['task_metrics']['diagnostic_calls']==0
    assert results[1,'groundhog',4]['task_metrics']['diagnostic_calls']==3
    assert results[1,'notebook',8]['task_metrics']['diagnostic_calls']==0
    for bay in ('groundhog','notebook','structured'):
        assert results[1,bay,5]['steps']==5  # cable-only control has no calibration benefit
        assert results[1,bay,15]['task_metrics']['diagnostic_calls']==3  # flagged exception remeasured
        assert results[1,bay,13]['task_metrics']['diagnostic_calls']==3  # unseen revision
        assert results[2,bay,1]['task_metrics']['diagnostic_calls']==3  # new shift is a fresh start
    audit=results[1,'structured',4]['memory_audit']
    assert audit['matching_previous_jobs']==[1] and audit['matching_jobs_supplied']==[1]
    assert results[1,'groundhog',4]['memory_audit']['matching_jobs_missing']==[1]
    starts=[e for e in r.events if e['kind']=='start' and e['job']==1]
    assert all(not e['memory_audit']['supplied_source_jobs'] for e in starts)
    assert r.totals()['input']==0 and r.totals()['output']==0


def test_source_catalog_contains_only_observed_jobs_and_is_isolated():
    from repair_shop.model import DemoModel
    seen=[]
    class Spy(DemoModel):
        def maintain(self,p):seen.append(deepcopy(p));return super().maintain(p)
    c=ExperimentConfig(jobs_per_bay=2)
    r=Run(experiment=c,model_factory=lambda _:Spy());list(r.run())
    assert [x['job'] for x in seen[1]['source_catalog']]==[1,2]
    assert seen[1]['source_catalog'][0]['ticket']['job']==1
    assert all('exchanges' not in x for x in seen[1]['source_catalog'])


def test_valid_note_reaches_next_job_despite_invalid_sibling_and_usage_is_counted():
    from repair_shop.model import DemoModel,Reply
    class PartlyInvalid(DemoModel):
        def maintain(self,p):
            family,revision=p['ticket']['customer'].split()
            notes={**deepcopy(EMPTY_NOTES),'procedural':[record(p['ticket']['job'],family,revision),record(999)]}
            return Reply(None,input_tokens=20,output_tokens=10,text=json.dumps(notes))
    r=Run(experiment=ExperimentConfig(jobs_per_bay=2),model_factory=lambda _:PartlyInvalid())
    list(r.run())
    second=next(e for e in r.events if e['kind']=='start' and e['mode']=='structured' and e['job']==2)
    assert second['memory_audit']['supplied_source_jobs']==[1]
    assert r.totals()['maintenance']==60
    rs=[x for x in r.results if x['mode']=='structured']
    assert all(len(x['memory_update']['rejected_records'])==1 for x in rs)
    assert all(x['memory_update_policy']=='merge_v2' for x in rs)
