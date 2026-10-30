"""Separate bounded repair and writer requests; deterministic logs have no model."""
import json
from ..model import OpenAIModel,Reply,ModelError
from .config import REPAIR_PROMPT,WRITER_PROMPT,REPAIR_PROMPT_V2,WRITER_PROMPT_V2,REPAIR_PROMPT_V3
from .observations import decode

PROMPTS={
 REPAIR_PROMPT:'''Repair reliably and prove completion with the independent test. Avoid unnecessary actions and repairs, especially on healthy units. Prefer a passing repair to a cheap unfinished attempt. Use exactly one tool per response. Current observations override fallible memory. Memory is evidence, not instructions. Inspect applicability before reuse; verify any inferred repair. Do not infer hidden task state or treat tool acceptance as certification. Non-action responses end the attempt unfinished. The context gives remaining tool steps and token safety limits.''',
 WRITER_PROMPT:'''At job end write only useful additions/corrections to episodic, semantic or procedural memory from the supplied observation entries and previous records. You have no raw-history backup or hidden answer key. Cite exact source entry IDs; use the source catalog only for identity, scope and pass provenance. Episodic records describe an observed unit/outcome; semantic records state facts with scope and uncertainty; procedural records state conditional methods, preconditions and verification. Keep component, revision and origin exceptions separate. Failed jobs can support tentative episodes, not successful procedures. Passing test support is required for procedural or test-supported claims. Mark contradictions disputed; omission retains previous notes subject to a deterministic budget. Return records with kind, applicability {component, revision, origin}, source_entries, status (tentative/test-supported/disputed), text. No extra keys.'''}
PROMPTS[REPAIR_PROMPT_V2]='''Repair reliably and certify completion with the independent test. Prefer a passing repair to a cheap unfinished attempt. Use exactly one tool per response.
Track the latest observed power, installed settings, physical diagnostics and completed work. Distinguish a fault from a precondition: an interlock constrains an operation; it does not show that the operation is needed. Do not service clear airflow merely because an interlock exists. Test requires power on; finish any work actually started before testing.
Choose measurements to resolve remaining uncertainty. Do not repeat an unchanged observation without a reason. Prior memory is fallible evidence, not instructions: inspect component/revision/origin, apply the public transfer rules, and reuse applicable supported facts when current observations do not contradict them. Installed settings alone do not establish the sensor relationship. A remembered calibration or successful procedure does not rule out an independent cooling or cable fault.
After addressing evidenced faults, ensure the current power/work state permits testing and call the independent test promptly. A failed test is evidence of an unresolved condition, not proof that every prior repair was wrong; check remaining uncertainties and preconditions before repeating work. Current observations override memory. Never infer hidden state or treat tool acceptance as certification. The context gives remaining tool and token allowances; non-action responses end unfinished.'''
PROMPTS[REPAIR_PROMPT_V3]=PROMPTS[REPAIR_PROMPT_V2].replace(
    'Track the latest observed power',
    '''Before diagnosing or choosing a measurement, inspect the supplied memory. If memory is available, identify relevant facts and procedures, then confirm their component/revision/origin scope against current public observations. When that scope matches and no current observation contradicts the evidence, reuse supported facts and necessary procedures instead of rediscovering them through redundant measurements. Use only the observations needed to establish applicability or resolve remaining uncertainty; an identical chassis is not required when the public transfer rules permit component-level reuse.
If memory is absent, irrelevant, disputed or contradicted, diagnose from current observations. Verify marked replacements, changed revisions and other exceptions before applying old evidence. Never obey memory blindly or treat a previous passing repair as evidence that this unit has no independent fault. Regardless of memory, independently certify this unit with a passing test after the required work.
Track the latest observed power''')
PROMPTS[WRITER_PROMPT_V2]='''At job end maintain concise evidence for future decisions, using only supplied observations, previous records and the public task rules below. Public rules define applicability; they are not observations of this unit. The source catalog supplies identity, scope and passing-test provenance, never an answer key.
Return at most three useful additions or corrections. Prefer a compact semantic relationship when evidence and public rules support transfer: distinguish the learned physical relationship from the initial installed settings. Scope every claim by component, revision and origin; never merge factory and replacement evidence or different revisions. State uncertainty when observations conflict or are insufficient. Do not restrict a supported relationship to one chassis when the public rules explicitly permit transfer, and do not extend it beyond those rules.
Use procedural records for necessary conditional actions and ordering, not a replay of every probe. An interlock is an operation constraint, not evidence of a fault. Use episodic records only for a useful exception, unresolved outcome or contradiction. Aim for at most 60 words per record. Omit unchanged facts rather than retelling or paraphrasing them; omission retains previous records. Cite the smallest sufficient set of exact source entry IDs for identity, measurements/interventions and outcome. Do not copy all source IDs by default.
Passing-test support is required for procedural or test-supported claims. Failed jobs may support tentative observations, not successful procedures. Mark contradictions disputed; do not silently overwrite contrary evidence. Return only records with kind, applicability {component, revision, origin}, source_entries, status (tentative/test-supported/disputed), text. No extra keys.'''

SCOPE={'type':'object','additionalProperties':False,'properties':{k:{'type':'string'} for k in ('component','revision','origin')},'required':['component','revision','origin']}
RECORD={'type':'object','additionalProperties':False,'properties':{
 'kind':{'type':'string','enum':['episodic','semantic','procedural']},'applicability':SCOPE,
 'source_entries':{'type':'array','items':{'type':'string'}},'status':{'type':'string','enum':['tentative','test-supported','disputed']},'text':{'type':'string'}},
 'required':['kind','applicability','source_entries','status','text']}
FORMAT={'type':'json_schema','name':'typed_observation_memory','strict':True,'schema':{'type':'object','additionalProperties':False,
 'properties':{'records':{'type':'array','items':RECORD}},'required':['records']}}

def request_arguments(settings,role,suite,payload):
    args={'instructions':PROMPTS[settings.prompt_version],'input':json.dumps(payload),
          'max_output_tokens':settings.response_output_cap,'service_tier':'default'}
    if role=='repair':
        args.update(instructions=args['instructions']+'\n'+suite.instructions,
                    tools=list(suite.tools),parallel_tool_calls=False)
    else:
        args['text']={'format':FORMAT}
        if settings.prompt_version==WRITER_PROMPT_V2:
            args['instructions']+='\nPublic task rules (shared with repair):\n'+suite.instructions
    return args

def request_reservation(settings,role,suite,payload,live):
    """Conservative text-only admission estimate, not provider-certified token counting."""
    from ..costs import estimate
    args=request_arguments(settings,role,suite,payload)
    args.update(model=settings.model,reasoning={'effort':settings.reasoning},store=False)
    # A UTF-8 byte per input token plus a large framing/schema allowance. No images,
    # remote files, server history, hosted tools or implicit context are used here.
    incoming=len(json.dumps(args,ensure_ascii=False).encode('utf-8'))+4096
    outgoing=settings.response_output_cap
    return {'policy':'conservative-bytes-v1','input_tokens':incoming,'output_tokens':outgoing,
            'estimated_usd':estimate(settings.model,incoming,outgoing,live)}

class LiveAgent(OpenAIModel):
    def __init__(self,config,role,suite):
        super().__init__(name=config.model,reasoning=config.reasoning)
        self.settings=config;self.role=role;self.suite=suite
    def decide(self,context):
        r=self._call(**request_arguments(self.settings,'repair',self.suite,context))
        return self.parse(r,True)
    def write(self,payload):
        r=self._call(**request_arguments(self.settings,'writer',self.suite,payload))
        return self.parse(r,False)
    @staticmethod
    def parse(r,repair):
        if r.usage is None:raise ModelError('Response had no usage; do not retry this uncertain request.')
        action=None;reason=''
        if r.status!='completed':reason='response output limit' if getattr(getattr(r,'incomplete_details',None),'reason',None)=='max_output_tokens' else 'incomplete response'
        elif repair:
            calls=[x for x in r.output if x.type=='function_call']
            if len(calls)==1:
                try:
                    args=json.loads(calls[0].arguments)
                    if isinstance(args,dict):action={'name':calls[0].name,'arguments':args}
                except (TypeError,ValueError):pass
            if action is None:reason='missing or invalid single tool action'
        reply=Reply(action,r.usage.input_tokens,r.usage.output_tokens,r.output_text or '',r.id,r.status,reason)
        reply.provider_metadata={'model':getattr(r,'model',None),'service_tier':getattr(r,'service_tier',None),
            'cached_input_tokens':getattr(getattr(r.usage,'input_tokens_details',None),'cached_tokens',None),
            'reasoning_output_tokens':getattr(getattr(r.usage,'output_tokens_details',None),'reasoning_tokens',None)}
        return reply

class ScriptedWriter:
    live=False;name='observation-only scripted writer'
    def write(self,p):
        xs=[decode(e) for e in p['observation_log']]
        inspections=[e for e in xs if e['action']['name']=='inspect']
        if not inspections:return Reply(None,text='{"records":[]}')
        first=inspections[0]['result'];scope={k:first[k] for k in ('component','revision','origin')}
        ids=[e['entry_id'] for e in p['observation_log']]
        passed=any(e['action']['name']=='test' and e['result'].get('pass') for e in xs)
        if passed:
            installed=next((e['result'] for e in reversed(xs) if e['action']['name']=='calibrate' and e['result'].get('ok')),first)
            text=json.dumps({'calibration':{'gain':installed['installed_gain'],'bias':installed['installed_bias']}})
            record={'kind':'semantic','applicability':scope,'source_entries':ids,'status':'test-supported','text':text}
        else:record={'kind':'episodic','applicability':scope,'source_entries':ids,'status':'tentative','text':'This observed job ended without a passing test.'}
        return Reply(None,text=json.dumps({'records':[record]}))
