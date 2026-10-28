"""Offline contract/compatibility checks; no claim about tuned model performance."""
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import pytest
from repair_shop.evaluation.config import AgentConfig,EvaluationConfig,preset,WRITER_PROMPT_V2
from repair_shop.evaluation.models import PROMPTS,request_arguments
from repair_shop.evaluation.runner import EvaluationRun
from repair_shop.evaluation.service import suite as v1
from repair_shop.evaluation.service_v2 import suite as v2
from repair_shop.evaluation.app import Controller,describe
from repair_shop.evaluation.storage import Store

ROOT=Path(__file__).resolve().parents[1]

def run(config):
    evaluation=EvaluationRun(config);list(evaluation.run());return evaluation

def test_published_v1_protocol_and_task_keep_historical_semantics():
    frozen=json.loads((ROOT/'docs/evaluation-results/2026-10-28/summary.json').read_text())['manifest']
    assert v1().fingerprint==frozen['task']['fingerprint']
    assert all(PROMPTS[key]==value for key,value in frozen['prompts'].items())
    for filename in ('evaluation-live-2026-10-28.json','evaluation-live-2026-10-28-50k.json'):
        raw=json.loads((ROOT/'examples'/filename).read_text());config=EvaluationConfig.from_dict(raw)
        assert json.loads(json.dumps(config.to_dict()))==raw
        writer=config.conditions[-1].writer
        assert request_arguments(writer,'writer',v1(),{})['instructions']==frozen['prompts'][writer.prompt_version]
    old_world=v1().create_world(v1().jobs[1]);old_world.call('power',{'state':'off'})
    assert old_world.call('test',{})=={'pass':False,'observation':'load certification did not pass'}
    assert preset().task_set=='service-v1' and preset().conditions[0].repair.prompt_version=='repair-objective-v1'

def test_tuned_world_cold_paths_memory_and_repeat_fault_are_observable():
    config=preset('tuned-v2');evaluation=run(config)
    assert not config.live and evaluation.state=='completed' and len(evaluation.attempts)==24
    assert all(row['certified'] and row['steps']<=20 for row in evaluation.attempts)
    assert v2().fingerprint!=v1().fingerprint and evaluation.manifest['task']['id']=='service-v2'
    for row in evaluation.attempts:
        if row['job']==2:assert not any(e['action']['name'] in ('calibrate','operate') for e in row['raw_events'])
        if row['job']==3:
            assert any(e['result'].get('continuity')=='intermittent' for e in row['raw_events'])
            assert any(e['action']['arguments'].get('operation')=='reseat_cable' for e in row['raw_events'])
        if row['job']==7:
            installed=[e['result'] for e in row['raw_events'] if e['action']['name']=='calibrate'][-1]
            assert (installed['installed_gain'],installed['installed_bias'])==(2,10)
        assert not any(key in json.dumps(row['raw_events']) for key in ('target_gain','target_bias','align_first','loose','restricted":'))
    assert evaluation.totals()['input']==evaluation.totals()['output']==0
    # Both memory policies can use the same observations; structured has no scripted advantage.
    rows={(row['condition'],row['job']):row for row in evaluation.attempts}
    assert rows['rolling',3]['steps']==rows['structured',3]['steps']<rows['none',3]['steps']

def test_tuned_compound_indication_and_power_feedback_do_not_certify_hidden_faults():
    world=v2().create_world(v2().jobs[7])
    assert world.inspect()['indicated_temperature']==40
    assert world.call('probe',{'channel':'thermal'})['reference_temperature']==80
    assert not world.call('test',{})['pass']
    world.call('power',{'state':'off'})
    assert 'requires power on' in world.call('test',{})['observation'] and not world.passed
    world.call('calibrate',{'gain':2,'bias':-12})
    world.call('power',{'state':'on'});assert not world.call('test',{})['pass']
    world.call('power',{'state':'off'})
    assert not world.call('operate',{'operation':'vent'})['ok']
    for operation in ('align','vent','seal'):assert world.call('operate',{'operation':operation})['ok']
    world.call('power',{'state':'on'});assert not world.call('test',{})['pass']
    world.call('power',{'state':'off'});world.call('operate',{'operation':'reseat_cable'})
    world.call('power',{'state':'on'});assert world.call('test',{})['pass']

def test_writer_v2_gets_only_public_task_rules_and_keeps_role_controls():
    config=preset('tuned-v2');condition=config.conditions[-1];task=v2()
    args=request_arguments(condition.writer,'writer',task,{'observation_log':[]})
    assert task.instructions in args['instructions'] and 'tools' not in args
    assert args['input']==json.dumps({'observation_log':[]}) and args['max_output_tokens']==2048
    assert not any(key in args['instructions'] for key in ('initial_gain','initial_bias','fixture_data','target_gain','align_first'))
    assert request_arguments(condition.repair,'repair',task,{})['tools']==list(task.tools)
    assert AgentConfig(prompt_version=WRITER_PROMPT_V2).validate('writer')
    with pytest.raises(ValueError):AgentConfig(prompt_version=WRITER_PROMPT_V2).validate('repair')
    with pytest.raises(ValueError):replace(condition.writer,prompt_version='job-end-writer-v3').validate('writer')

@pytest.mark.parametrize('count',[2,3])
def test_tuned_production_callbacks_preserve_old_versions_and_exact_condition_count(tmp_path,count):
    ctl=Controller(Store(tmp_path/'evaluations.sqlite3'),tmp_path/'exports')
    old=replace(preset(),jobs=1);ref,*_=ctl.save_config(json.dumps(old.to_dict()),None,False)
    new=replace(preset('tuned-v2'),conditions=preset('tuned-v2').conditions[:count],jobs=3,repetitions=2)
    newer,*_=ctl.save_config(json.dumps(new.to_dict()),ref,False)
    assert newer['version']==2 and ctl.store.load_config(ref)==old
    restored,_,_=ctl.load_config(f"{newer['id']}:{newer['version']}")
    assert EvaluationConfig.from_dict(json.loads(restored))==new and 'service-v2' in describe(new)
    request=SimpleNamespace(session_hash='tuned')
    list(ctl.start(restored,False,request));first=ctl.session(request)['run']
    assert first.state=='completed' and len(first.attempts)==6*count and all(r['certified'] for r in first.attempts)
    assert all(not r['memory_supply_audit']['supplied_ids'] for r in first.attempts if r['job']==1)
    paths=ctl.download(request);saved=json.loads(Path(paths[1]).read_text())
    assert saved['manifest']['config']==json.loads(restored) and saved['manifest']['task']['fingerprint']==v2().fingerprint
    calls=len(first.calls);list(ctl.replay(request));assert len(first.calls)==calls
    ctl.reset(request);ctl.load_run(first.id,request)
    assert ctl.session(request)['saved']['manifest']==first.manifest
