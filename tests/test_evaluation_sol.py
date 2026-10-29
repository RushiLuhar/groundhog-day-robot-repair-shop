"""Offline controls and mixed-model pricing for the bounded Sol comparison."""
import json
from dataclasses import replace
from pathlib import Path
import pytest
from repair_shop.costs import estimate
from repair_shop.evaluation.config import EvaluationConfig
from repair_shop.evaluation.models import PROMPTS,ScriptedWriter
from repair_shop.evaluation.service import ServiceDemo
from repair_shop.evaluation.runner import EvaluationRun
from repair_shop.evaluation.storage import Store
from repair_shop.tasks import get_evaluation_suite

ROOT=Path(__file__).resolve().parents[1]

def sol_config():
    return EvaluationConfig.from_dict(json.loads((ROOT/'examples/evaluation-live-2026-10-29-sol.json').read_text()))

def test_sol_changes_only_repair_model_from_frozen_luna_and_roundtrips(tmp_path):
    frozen=json.loads((ROOT/'docs/evaluation-results/2026-10-28-tuned/summary.json').read_text())['manifest']
    config=sol_config();normalized=config.to_dict()
    normalized['name']=frozen['config']['name']
    for condition in normalized['conditions']:
        assert condition['repair']['model']=='gpt-6-sol' and condition['writer']['model']=='gpt-6-luna'
        condition['repair']['model']='gpt-6-luna'
    assert json.loads(json.dumps(normalized))==frozen['config']
    assert PROMPTS==frozen['prompts']
    suite=get_evaluation_suite(config.task_set,config.variant)
    assert suite.public_description()==frozen['task'] and suite.instructions==frozen['task_instructions']
    assert list(suite.tools)==frozen['tools']
    store=Store(tmp_path/'sol.sqlite3');ref=store.save_config(config)
    assert store.load_config(ref)==config and config.attempts==72

def test_mixed_sol_repair_luna_writer_accounting_uses_role_prices():
    class Repair(ServiceDemo):
        def decide(self,context):
            reply=super().decide(context);reply.input_tokens=500;reply.output_tokens=25;return reply
    class Writer(ScriptedWriter):
        def write(self,payload):
            reply=super().write(payload);reply.input_tokens=1000;reply.output_tokens=100;return reply
    config=sol_config();config=replace(config,jobs=1,repetitions=1,conditions=(config.conditions[-1],))
    run=EvaluationRun(config,agent_factory=lambda settings,role,suite:Repair() if role=='repair' else Writer())
    list(run.run())
    assert run.state=='completed' and run.attempts[0]['certified']
    repairs=[c for c in run.calls if c['role']=='repair'];writers=[c for c in run.calls if c['role']=='writer']
    assert len(repairs)==9 and len(writers)==1
    assert all(c['model']=='gpt-6-sol' and c['cost_usd']==pytest.approx(.00125) for c in repairs)
    assert writers[0]['model']=='gpt-6-luna' and writers[0]['cost_usd']==pytest.approx(.00015)
    assert run.totals()['estimated_usd']==pytest.approx(.0114)
    assert estimate('gpt-6-sol',300000,1000)==pytest.approx(1.215)
    assert estimate('gpt-6-astra',1000,1000) is None

def test_sol_usd_guard_prevents_outbound_call_without_unknown_usage():
    class Never:
        def decide(self,payload):raise AssertionError('USD guard must refuse before calling model')
    config=sol_config();config=replace(config,run_estimated_usd_limit=.000001)
    run=EvaluationRun(config,agent_factory=lambda *args:Never());list(run.run())
    assert run.state=='stopped' and 'USD admission guard' in run.stop_reason
    assert not run.calls and run.totals()['unknown_calls']==0
    assert run.attempts[0]['status']=='interrupted' and sum(r['status']=='unattempted' for r in run.attempts)==71
