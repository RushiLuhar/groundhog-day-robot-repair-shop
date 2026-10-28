"""Learning opportunities with costly observations, delayed reuse and counterexamples."""
import json
from dataclasses import dataclass
from ..model import DemoModel, Reply

AXES=('x','y','z')
TOOLS=tuple({'type':'function','name':name,'description':desc,'strict':True,
 'parameters':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}}
 for name,desc,props in [
 ('inspect','Read robot identity, module markings, cable continuity, power and current calibration. Does not reveal the correct calibration.',{}),
 ('measure','Measure one calibration axis. Signed error is current minus required value. Each measurement costs one tool step.',{'axis':{'type':'string','enum':list(AXES)}}),
 ('power','Switch supply on or off. Calibration and cable service require power off; measurements and load tests require power on.',{'state':{'type':'string','enum':['on','off']}}),
 ('apply_calibration','Set all three integer calibration values while power is off. Values are 1..9. Acceptance confirms a write, not correctness.',{a:{'type':'integer','minimum':1,'maximum':9} for a in AXES}),
 ('reseat_cable','Reconnect a loose cable while power is off.',{}),
 ('test','Run under load. Only a passing test completes the repair; reports symptoms, not the correct calibration.',{})])
INSTRUCTIONS='''Calibrations may be reusable for factory modules of the same robot family and revision.
Inspect every unit: replacement-module markings warn that factory calibration may not apply.
Different revisions may require different values. Current readings override memories.
measure reports signed error = current value minus required value; derive each required value from that observation.
You may reuse remembered calibration values, but only a passing test proves this unit repaired.
Some tickets have only a loose cable, with calibration already stable; these are controls where prior calibration offers no benefit.
Power must be on for measurements and testing, and off for calibration and cable service.
All required facts are observable through tools. There is no manual, hidden answer-key access or extra free measurement.'''

@dataclass(frozen=True)
class LearningJob:
    number:int
    family:str
    revision:str
    target:tuple[int,int,int]
    phase:str
    calibration_fault:bool=True
    cable_fault:bool=False
    replacement:bool=False

    def ticket(self):
        return {'job':self.number,'customer':f'{self.family} {self.revision}','complaint':'stops under load'}

# Phase labels are evaluation metadata only, never included in agent context.
SCHEDULE=(
 ('Amber','R1','discovery'),('Mint','R1','discovery'),('Violet','R1','discovery'),
 ('Amber','R1','early repeat'),('Birch','R1','control'),('Mint','R1','early repeat'),
 ('Violet','R1','early repeat'),('Violet','R1','immediate repeat'),('Amber','R1','delayed repeat'),
 ('Mint','R1','compound repeat'),('Violet','R1','delayed repeat'),('Birch','R1','control'),
 ('Amber','R2','revision change'),('Mint','R1','delayed repeat'),('Violet','R1','exception'),
 ('Amber','R1','old revision return'),('Amber','R2','revision repeat'),('Birch','R1','control'),
 ('Violet','R1','factory return'),('Mint','R2','revision change'),('Amber','R2','compound repeat'),
 ('Mint','R2','revision repeat'),('Violet','R1','delayed repeat'),('Birch','R1','control'),
 ('Amber','R1','exception'),('Mint','R1','old revision return'),('Amber','R1','factory return'),
 ('Violet','R2','revision change'),('Mint','R2','delayed repeat'),('Violet','R2','revision repeat'),
 ('Birch','R1','control'),('Amber','R2','delayed repeat'))
TARGETS={('Amber','R1'):(2,7,4),('Mint','R1'):(6,3,8),('Violet','R1'):(4,9,2),
         ('Amber','R2'):(8,2,5),('Mint','R2'):(3,8,1),('Violet','R2'):(7,1,6),('Birch','R1'):(5,5,5)}
JOBS=tuple(LearningJob(i,f,r,(9,4,7) if phase=='exception' else TARGETS[f,r],phase,
                     phase!='control',phase in ('control','compound repeat'),phase=='exception')
           for i,(f,r,phase) in enumerate(SCHEDULE,1))

class LearningWorld:
    def __init__(self,job):
        self.job=job;self.passed=False;self.power_on=True
        self.values=[0,0,0] if job.calibration_fault else list(job.target)
        self.cable_loose=job.cable_fault;self.measurements=0;self.invalid_actions=0;self.failed_tests=0;self.writes=0

    def inspect(self):
        return {**self.job.ticket(),'power':'on' if self.power_on else 'off','calibration':dict(zip(AXES,self.values)),
                'calibration_status':'unstable' if tuple(self.values)!=self.job.target else 'stable',
                'cable_continuity':'intermittent' if self.cable_loose else 'steady',
                'module_marking':'replacement module: factory calibration may not apply' if self.job.replacement else 'factory module'}

    def reject(self,message):
        self.invalid_actions+=1
        return {'ok':False,'observation':message}

    def call(self,name,args):
        if not isinstance(args,dict):return self.reject('Invalid arguments.')
        if name=='inspect' and not args:return self.inspect()
        if name=='power' and set(args)=={'state'} and args['state'] in ('on','off'):
            self.power_on=args['state']=='on';return {'ok':True,'power':args['state']}
        if name=='measure' and set(args)=={'axis'} and args['axis'] in AXES:
            if not self.power_on:return self.reject('Measurement requires power on.')
            self.measurements+=1;i=AXES.index(args['axis'])
            return {'axis':args['axis'],'current':self.values[i],'signed_error':self.values[i]-self.job.target[i]}
        if name=='apply_calibration' and set(args)==set(AXES) and all(type(v) is int and 1<=v<=9 for v in args.values()):
            if self.power_on:return self.reject('Electrical service interlock: supply is live.')
            self.values=[args[a] for a in AXES];self.writes+=1
            return {'ok':True,'written':dict(zip(AXES,self.values))}
        if name=='reseat_cable' and not args:
            if self.power_on:return self.reject('Electrical service interlock: supply is live.')
            self.cable_loose=False;return {'ok':True,'cable_continuity':'steady'}
        if name=='test' and not args:
            self.passed=self.power_on and not self.cable_loose and tuple(self.values)==self.job.target
            if not self.passed:self.failed_tests+=1
            return {'pass':self.passed,'observation':'runs steadily under load' if self.passed else 'supply is off' if not self.power_on else 'stops under load'}
        return self.reject('Unknown action or invalid arguments.')

    def snapshot(self):return self.inspect()
    def metrics(self):
        return {'diagnostic_calls':self.measurements,'invalid_actions':self.invalid_actions,
                'failed_tests':self.failed_tests,'calibration_writes':self.writes,'phase':self.job.phase}

class LearningDemo(DemoModel):
    """Scripted mechanism check, not evidence of model performance. Reads observations only."""
    def remembered(self,prior,customer):
        if isinstance(prior,dict):
            for r in reversed(prior.get('procedural',[])):
                if f"{r['model']} {r['revision']}"==customer:
                    try:
                        v=json.loads(r['text']).get('calibration')
                        if isinstance(v,dict) and set(v)==set(AXES):return v
                    except (ValueError,TypeError):pass
        elif isinstance(prior,list):
            factory={x['ticket']['job'] for x in prior if x['action']['name']=='inspect' and x['result'].get('module_marking')=='factory module'}
            passed={x['ticket']['job'] for x in prior if x['result'].get('pass') and x['ticket']['customer']==customer}
            for x in reversed(prior):
                if x['ticket']['job'] in passed & factory and x['result'].get('ok') and x['action']['name']=='apply_calibration':return x['result']['written']
        return None

    def decide(self,c):
        xs=c['current_job_exchanges']
        def act(name,**args):return Reply({'name':name,'arguments':args})
        if not xs:return act('inspect')
        visible=xs[0]['result'];power=next((x['result']['power'] for x in reversed(xs) if 'power' in x['result']),'on')
        operations=[x['action']['name'] for x in xs if x['result'].get('ok')]
        failed=any(x['action']['name']=='test' and not x['result'].get('pass') for x in xs)
        values=self.remembered(c['prior_memory'],c['ticket']['customer'])
        if failed or visible['module_marking']!='factory module':values=None
        if visible['calibration_status']=='unstable' and 'apply_calibration' not in operations:
            readings={x['result']['axis']:x['result'] for x in xs if x['action']['name']=='measure' and 'signed_error' in x['result']}
            if not values:
                for a in AXES:
                    if a not in readings:return act('measure',axis=a)
                values={a:readings[a]['current']-readings[a]['signed_error'] for a in AXES}
            if power=='on':return act('power',state='off')
            return act('apply_calibration',**values)
        if visible['cable_continuity']=='intermittent' and 'reseat_cable' not in operations:
            if power=='on':return act('power',state='off')
            return act('reseat_cable')
        if power=='off':return act('power',state='on')
        return act('test')

    def maintain(self,p):
        writes=[x['result']['written'] for x in p['exchanges'] if x['action']['name']=='apply_calibration' and x['result'].get('ok')]
        original=p['exchanges'][0]['result'] if p['exchanges'] else {}
        notes={'episodic':[],'semantic':[],'procedural':[]}
        if p['passed'] and writes and original.get('module_marking')=='factory module':
            family,revision=p['ticket']['customer'].split()
            notes['procedural']=[{'model':family,'revision':revision,'source_jobs':[p['ticket']['job']],
                'status':'test-supported','text':json.dumps({'calibration':writes[-1]})}]
        return Reply(None,text=json.dumps(notes))
