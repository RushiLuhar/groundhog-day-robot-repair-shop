"""Whole-entry rolling history and versioned, auditable typed-record retention."""
from copy import deepcopy
import hashlib,json
from .observations import tokens,supplied

EMPTY={'records':[]}

def identifier(record):return hashlib.sha256(json.dumps(record,sort_keys=True).encode()).hexdigest()[:16]

def suffix(entries,limit,budget):
    kept=[]
    for e in reversed(entries):
        trial=[e]+kept
        if len(trial)>limit or tokens(supplied(trial))>budget:break
        kept=trial
    return deepcopy(kept)

def select_records(records,budget):
    kept=[];excluded=[]
    for r in records:
        if tokens({'records':kept+[r]})<=budget:kept.append(r)
        else:excluded.append(r['id'])
    return deepcopy(kept),excluded

class Memory:
    def __init__(self):self.history=[];self.records=[];self.catalog={};self.ordinal=0
    def observe(self,entries):
        scope={}
        for e in entries:
            if e['action']['name']=='inspect' and all(k in e['result'] for k in ('component','revision','origin')):
                scope={k:e['result'][k] for k in ('component','revision','origin')}
            self.ordinal+=1
            self.catalog[e['entry_id']]={'job':e['job'],'applicability':deepcopy(scope),
                'passed_test':e['action']['name']=='test' and e['result'].get('pass') is True,'ordinal':self.ordinal}
    def supply(self,c):
        if c.memory=='none':return [],{'supplied_ids':[],'supply_tokens':tokens([]),'partial_jobs':[]}
        if c.memory=='rolling':
            kept=suffix(self.history,c.rolling_entry_limit,c.supply_tokens)
            ids=[e['entry_id'] for e in kept]
            jobs={e['job'] for e in kept}
            partial=[j for j in sorted(jobs) if any(v['job']==j and k not in ids for k,v in self.catalog.items())]
            return supplied(kept),{'supplied_ids':ids,'supply_tokens':tokens(supplied(kept)),'partial_jobs':partial}
        kept,excluded=select_records(self.records,c.supply_tokens)
        return {'records':kept},{'supplied_ids':[r['id'] for r in kept],'excluded_ids':excluded,
            'source_entry_ids':sorted({i for r in kept for i in r['source_entries']}),'supply_tokens':tokens({'records':kept})}
    def retain_rolling(self,entries,c):
        candidates=self.history+deepcopy(entries)
        self.history=suffix(candidates,c.rolling_entry_limit,c.retention_tokens)
        ids={e['entry_id'] for e in self.history}
        return {'retained_ids':sorted(ids),'evicted_ids':[e['entry_id'] for e in candidates if e['entry_id'] not in ids]}
    def merge(self,text,c):
        incoming=json.loads(text)
        if not isinstance(incoming,dict) or set(incoming)!={'records'} or not isinstance(incoming['records'],list):raise ValueError('Expected a records list.')
        candidates=deepcopy(self.records);accepted=[];rejected=[]
        fields={'kind','applicability','source_entries','status','text'}
        for index,r in enumerate(incoming['records']):
            try:
                if not isinstance(r,dict) or set(r)!=fields:raise ValueError('Invalid record fields.')
                if r['kind'] not in ('episodic','semantic','procedural') or r['status'] not in ('tentative','test-supported','disputed'):raise ValueError('Invalid record type/status.')
                if not isinstance(r['text'],str) or not r['text'].strip():raise ValueError('Empty record text.')
                scope=r['applicability'];ids=r['source_entries']
                if not isinstance(scope,dict) or set(scope)!={'component','revision','origin'} or any(not isinstance(v,str) for v in scope.values()):raise ValueError('Invalid applicability.')
                if not isinstance(ids,list) or not ids or any(not isinstance(i,str) or i not in self.catalog for i in ids):raise ValueError('Unknown source entry.')
                if any(self.catalog[i]['applicability']!=scope for i in ids):raise ValueError('Source applicability mismatch.')
                if (r['kind']=='procedural' or r['status']=='test-supported') and not any(self.catalog[i]['passed_test'] for i in ids):raise ValueError('Successful claim needs a cited passing test.')
                record={**deepcopy(r),'id':identifier(r)}
                if tokens({'records':[record]})>c.retention_tokens:raise ValueError('Record exceeds retention budget.')
                candidates.append(record);accepted.append(record['id'])
            except (ValueError,TypeError,KeyError) as e:rejected.append({'index':index,'reason':str(e)})
        distinct={};dedup=[]
        def age(r):return max(self.catalog[i]['ordinal'] for i in r['source_entries'])
        for r in candidates:
            key=json.dumps({k:r[k] for k in ('kind','applicability','status','text')},sort_keys=True)
            if key in distinct:
                old=distinct[key]
                if age(r)>=age(old):dedup.append(old['id']);distinct[key]=r
                else:dedup.append(r['id'])
            else:distinct[key]=r
        priority={'procedural':0,'semantic':1,'episodic':2}
        ordered=sorted(distinct.values(),key=lambda r:(-age(r),priority[r['kind']],r['id']))
        old={r['id'] for r in self.records}
        self.records,evicted=select_records(ordered,c.retention_tokens)
        kept={r['id'] for r in self.records}
        return {'accepted_ids':accepted,'rejected':rejected,'deduplicated_ids':dedup,'evicted_ids':evicted,
                'removed_prior_ids':sorted(old-kept),'retained_ids':sorted(kept),
                'omitted_prior_ids':[r['id'] for r in candidates[:len(old)] if r['id'] not in accepted],
                'retention_tokens':tokens({'records':self.records})}
