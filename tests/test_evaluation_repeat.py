"""Offline A-to-A controls; scripted outcomes are not live model evidence."""
import json
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace
import pytest
from repair_shop.evaluation.config import EvaluationConfig
from repair_shop.evaluation.models import request_arguments
from repair_shop.evaluation.observations import supplied, tokens
from repair_shop.evaluation.runner import EvaluationRun
from repair_shop.evaluation.storage import Store
from repair_shop.evaluation.app import Controller, describe
from repair_shop.tasks import get_evaluation_suite

ROOT=Path(__file__).resolve().parents[1]


def config():
    return EvaluationConfig.from_dict(json.loads((ROOT/'examples/evaluation-live-2026-10-29-repeat.json').read_text()))


def test_repeat_changes_only_sequence_and_preserves_frozen_tuned_controls(tmp_path):
    c=config();old=json.loads((ROOT/'examples/evaluation-live-2026-10-28-tuned.json').read_text())
    normalized=c.to_dict()
    for k in ('name','task_set','jobs'):normalized[k]=old[k]
    assert json.loads(json.dumps(normalized))==old
    assert c.attempts==18 and c.jobs==2 and c.repetitions==3
    store=Store(tmp_path/'repeat.sqlite3');ref=store.save_config(c)
    assert store.load_config(ref)==c
    with pytest.raises(ValueError):replace(c,jobs=3).validate()
    assert '2 of 2 tickets' in describe(c) and '18 attempts' in describe(c)


def test_repeat_world_is_identical_fresh_state_with_independent_certification():
    task=get_evaluation_suite('service-repeat-v1');base=get_evaluation_suite('service-v2')
    a,b=task.jobs
    assert a==base.jobs[0] and b==replace(a,number=2)
    assert asdict(a)|{'number':2}==asdict(b)
    assert a.ticket()|{'job':2}==b.ticket()
    wa,wb=task.create_world(a),task.create_world(b)
    assert wa.inspect()==wb.inspect() and not wa.passed and not wb.passed
    assert not wb.call('test',{})['pass']
    wa.call('power',{'state':'off'});wa.call('calibrate',{'gain':a.gain,'bias':a.bias})
    wa.call('power',{'state':'on'});assert wa.call('test',{})['pass']
    assert wb.inspect()['installed_gain']==b.initial_gain and not wb.passed
    assert not wb.call('test',{})['pass']
    assert task.fingerprint!=base.fingerprint
    for role in ('repair','writer'):
        setting=getattr(config().conditions[-1],role)
        assert request_arguments(setting,role,task,{})==request_arguments(setting,role,base,{})


def test_repeat_retains_and_supplies_complete_first_log_and_resets_each_pair():
    c=replace(config(),live=False);run=EvaluationRun(c);list(run.run())
    assert run.state=='completed' and len(run.attempts)==18 and all(r['certified'] for r in run.attempts)
    assert run.manifest['condition_order_by_repetition']==[['none','rolling','structured'],['rolling','structured','none'],['structured','none','rolling']]
    for rep in range(1,4):
        for condition in c.conditions:
            a,b=[r for r in run.attempts if r['repetition']==rep and r['condition']==condition.id]
            assert not a['memory_supply_audit']['supplied_ids']
            assert a['raw_events'][0]['result']==b['raw_events'][0]['result']
            assert sum(e['action']['name']=='sample_sensor' for e in a['raw_events'])==2
            assert b['raw_events'][-1]['action']['name']=='test' and b['raw_events'][-1]['result']['pass']
            if condition.memory=='none':
                assert not b['memory_input']
                assert sum(e['action']['name']=='sample_sensor' for e in b['raw_events'])==2
            elif condition.memory=='rolling':
                ids=[e['entry_id'] for e in a['observation_log']]
                assert len(ids)<=condition.rolling_entry_limit
                assert tokens(supplied(a['observation_log']))<=min(condition.retention_tokens,condition.supply_tokens)
                assert b['memory_input']==a['memory_after']==supplied(a['observation_log'])
                assert b['memory_supply_audit']['supplied_ids']==ids and not b['memory_supply_audit']['partial_jobs']
            else:
                assert b['memory_input']['records']==a['memory_after'] and a['memory_after']
                ids={e['entry_id'] for e in a['raw_events']}
                assert set(b['memory_supply_audit']['source_entry_ids'])<=ids
                assert a['raw_events'][-1]['entry_id'] in b['memory_supply_audit']['source_entry_ids']
    assert run.totals()['input']==run.totals()['output']==0


def test_repeat_production_callbacks_persist_replay_reset_and_run_again(tmp_path):
    ctl=Controller(Store(tmp_path/'repeat.sqlite3'),tmp_path/'exports');request=SimpleNamespace(session_hash='repeat')
    c=replace(config(),live=False);text=json.dumps(c.to_dict())
    ref,*_=ctl.save_config(text,None,False)
    restored,_,_=ctl.load_config(f"{ref['id']}:{ref['version']}")
    assert EvaluationConfig.from_dict(json.loads(restored))==c
    list(ctl.start(restored,False,request));first=ctl.session(request)['run']
    assert len(first.attempts)==18 and first.state=='completed'
    paths=ctl.download(request);saved=json.loads(Path(paths[1]).read_text())
    assert saved['manifest']==first.manifest
    calls=len(first.calls);list(ctl.replay(request));assert len(first.calls)==calls
    ctl.reset(request);ctl.load_run(first.id,request)
    assert ctl.session(request)['saved']['manifest']==first.manifest
    ctl.reset(request);list(ctl.start(restored,False,request));second=ctl.session(request)['run']
    assert second.id!=first.id and all(not r['memory_supply_audit']['supplied_ids'] for r in second.attempts if r['job']==1)
