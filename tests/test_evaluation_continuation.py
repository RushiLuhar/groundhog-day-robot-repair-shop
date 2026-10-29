"""Explicit authorized spend extension, never crash recovery or paid retries."""
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import pytest
from repair_shop.costs import estimate
from repair_shop.evaluation.config import EvaluationConfig
from repair_shop.evaluation.runner import EvaluationRun,continue_unattempted
from repair_shop.evaluation.models import ScriptedWriter
from repair_shop.evaluation.service import ServiceDemo
from repair_shop.evaluation.storage import Store

class Repair(ServiceDemo):
    def decide(self,context):
        reply=super().decide(context);reply.input_tokens=500;reply.output_tokens=25;return reply
class Writer(ScriptedWriter):
    def write(self,payload):
        reply=super().write(payload);reply.input_tokens=1000;reply.output_tokens=100;return reply

def factory(settings,role,suite):return Repair() if role=='repair' else Writer()

@pytest.fixture
def stopped(monkeypatch):
    def reservation(settings,role,suite,payload,live):
        incoming,outgoing=(500,25) if role=='repair' else (1000,100)
        return {'policy':'conservative-bytes-v1','input_tokens':incoming,'output_tokens':outgoing,
                'estimated_usd':estimate(settings.model,incoming,outgoing,live)}
    monkeypatch.setattr('repair_shop.evaluation.runner.request_reservation',reservation)
    config=EvaluationConfig.from_dict(json.loads((Path(__file__).resolve().parents[1]/'examples/evaluation-live-2026-10-29-sol.json').read_text()))
    config=replace(config,run_estimated_usd_limit=.05)
    run=EvaluationRun(config,agent_factory=factory);list(run.run())
    assert run.state=='stopped' and any(r['condition']=='structured' and r['certified'] for r in run.attempts)
    return run.report(),replace(config,run_estimated_usd_limit=10)

def test_continuation_preserves_calls_memory_attempts_and_immutable_prior(stopped,tmp_path):
    prior,config=stopped;original=deepcopy(prior)
    started=[r for r in prior['attempts'] if r['status']!='unattempted']
    db=Store(tmp_path/'continued.sqlite3')
    run=continue_unattempted(prior,config,agent_factory=factory,on_checkpoint=db.checkpoint)
    assert run.totals()==prior['usage'] and run.elapsed_seconds==prior['elapsed_seconds']
    assert run.manifest['continuation']['prior_manifest']==prior['manifest']
    assert run.manifest['config']['run_estimated_usd_limit']==10
    assert run.manifest['config']['run_total_token_limit']==prior['manifest']['config']['run_total_token_limit']
    db.begin(run);yielded=list(run.run());final=run.report()
    assert len(yielded)==72-len(started) and run.state=='completed'
    assert prior==original and final['attempts'][:len(started)]==started
    assert final['calls'][:len(prior['calls'])]==prior['calls']
    assert final['elapsed_seconds']>=prior['elapsed_seconds']
    ended=[(e['repetition'],e['condition'],e['job']) for e in final['events'] if e['kind']=='attempt_ended']
    assert len(ended)==len(set(ended))==72
    assert sum(r['status']=='interrupted' for r in final['attempts'])==1
    assert all(r['certified'] for r in yielded)
    assert all(not r['memory_supply_audit']['supplied_ids'] for r in yielded if r['job']==1)
    assert db.load(run.id)['usage']==final['usage']
    with pytest.raises(ValueError):list(run.run())

def test_continuation_combined_cost_guard_includes_every_prior_charge(stopped):
    prior,config=stopped;config=replace(config,run_estimated_usd_limit=.05001)
    class Never:
        def decide(self,p):raise AssertionError('Prior charges must prevent this request')
    run=continue_unattempted(prior,config,agent_factory=lambda *a:Never());list(run.run())
    assert run.state=='stopped' and run.calls==prior['calls']
    assert run.totals()==prior['usage']

@pytest.mark.parametrize('change',['unknown','error','changed_model','changed_tokens','changed_memory','bad_fingerprint','bad_observation','bad_memory'])
def test_continuation_refuses_uncertain_or_changed_contract_before_client_construction(stopped,change):
    prior,config=stopped;prior=deepcopy(prior)
    if change=='unknown':prior['calls'][0]['status']='unknown'
    elif change=='error':prior['state']='error'
    elif change=='changed_model':config=replace(config,conditions=(replace(config.conditions[0],repair=replace(config.conditions[0].repair,model='gpt-6-luna')),)+config.conditions[1:])
    elif change=='changed_tokens':config=replace(config,run_total_token_limit=2000001)
    elif change=='changed_memory':config=replace(config,conditions=(replace(config.conditions[0],supply_tokens=1999),)+config.conditions[1:])
    elif change=='bad_fingerprint':prior['manifest']['source']['commit']='changed'
    elif change=='bad_observation':prior['attempts'][0]['raw_events'][0]['result']['origin']='replacement'
    elif change=='bad_memory':next(r for r in prior['attempts'] if r['condition']=='structured')['memory_after']=[]
    def forbidden(*a):raise AssertionError('Validation must happen before clients are built')
    with pytest.raises(ValueError):continue_unattempted(prior,config,agent_factory=forbidden)
