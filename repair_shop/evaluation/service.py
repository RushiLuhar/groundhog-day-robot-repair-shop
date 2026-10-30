"""Eight deterministic service tickets. Private fixtures never enter observations."""
from dataclasses import dataclass,asdict
from ..tasks.base import TaskSuite
from ..model import Reply
from .observations import decode
import json

TOOLS=tuple({'type':'function','name':name,'description':desc,'strict':True,
 'parameters':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}}
 for name,desc,props in [
 ('inspect','Read chassis, sensor component/revision/origin markings, installed calibration, indication, power and visible cooler work.',{}),
 ('sample_sensor','Read raw sensor response at a low or high reference temperature. Requires power on. The installed calibration does not change raw response.',{'level':{'type':'string','enum':['low','high']}}),
 ('probe','Read thermal airflow and reference temperature, cable continuity, or cooler interlocks. No free sensor samples.',{'channel':{'type':'string','enum':['thermal','continuity','interlocks']}}),
 ('power','Switch power on or off. Mechanical service and calibration require power off; sampling and testing require power on.',{'state':{'type':'string','enum':['on','off']}}),
 ('operate','With power off, align the controller, vent the loop, seal completed work, or reseat the cable. Probe interlocks to discover ordering constraints.',{'operation':{'type':'string','enum':['align','vent','seal','reseat_cable']}}),
 ('calibrate','Install gain (1..4) and bias (-20..20), with power off. A write is not proof of repair.',{'gain':{'type':'integer','minimum':1,'maximum':4},'bias':{'type':'integer','minimum':-20,'maximum':20}}),
 ('test','Independently certify sensor accuracy at two references, true thermal safety, continuity, power and completed mechanical work.',{})])
INSTRUCTIONS='''Raw sensor response s = g*T + b. Displayed temperature = (s - installed_bias) / installed_gain.
Low and high sample tools expose raw response and independent reference T. Derive the unknown g and b from evidence.
Calibration changes the indication, never the true temperature. A restricted cooler still fails certification even if its display looks safe.
A cable can cause the same complaint; a healthy unit may need no service. Physical cooling is safe at or below 60 degrees.
Sensor calibration can transfer across chassis when component, revision and origin markings match.
A replacement or new revision may invalidate earlier calibration. Inspect the current unit before applying memory.
Cooler interlocks determine whether vent or align comes first. Both must precede seal. Electrical/mechanical work requires power off.
All facts needed for a cold repair are observable. Only the independent test certifies a repair.'''

@dataclass(frozen=True)
class ServiceJob:
    number:int
    chassis:str
    revision:str
    origin:str
    gain:int
    bias:int
    initial_gain:int
    initial_bias:int
    restricted:bool=False
    loose:bool=False
    align_first:bool=False
    def ticket(self):return {'job':self.number,'customer':self.chassis+' R1','complaint':'intermittent shutdown under load'}

class ServiceWorld:
    def __init__(self,job):
        self.job=job;self.gain=job.initial_gain;self.bias=job.initial_bias
        self.restricted=job.restricted;self.loose=job.loose;self.progress=[]
        self.power=True;self.passed=False;self.measurements=0;self.invalid=0
    def temperature(self):return 80 if self.restricted else 40
    def inspect(self):return {'chassis':self.job.chassis,'component':'TS-7','revision':self.job.revision,
        'origin':self.job.origin,'installed_gain':self.gain,'installed_bias':self.bias,
        'indicated_temperature':(self.job.gain*self.temperature()+self.job.bias-self.bias)/self.gain,
        'power':'on' if self.power else 'off','visible_work':list(self.progress)}
    def reject(self,why):self.invalid+=1;return {'ok':False,'observation':why}
    def call(self,name,args):
        if not isinstance(args,dict):return self.reject('Invalid arguments.')
        if name=='inspect' and not args:return self.inspect()
        if name=='sample_sensor' and set(args)=={'level'} and args['level'] in ('low','high'):
            if not self.power:return self.reject('Sampling requires power on.')
            self.measurements+=1;t=30 if args['level']=='low' else 70
            return {'level':args['level'],'reference_temperature':t,'raw_reading':self.job.gain*t+self.job.bias}
        if name=='probe' and set(args)=={'channel'} and args['channel'] in ('thermal','continuity','interlocks'):
            self.measurements+=1
            if args['channel']=='thermal':return {'airflow':'restricted' if self.restricted else 'clear','reference_temperature':self.temperature()}
            if args['channel']=='continuity':return {'continuity':'intermittent' if self.loose else 'steady'}
            return {'alignment_interlock':'clear' if self.job.align_first or 'vent' in self.progress else 'pressure prevents alignment',
                    'vent_interlock':'alignment lock engaged' if self.job.align_first and 'align' not in self.progress else 'clear'}
        if name=='power' and set(args)=={'state'} and args['state'] in ('on','off'):
            self.power=args['state']=='on';return {'ok':True,'power':args['state']}
        if name=='operate' and set(args)=={'operation'} and args['operation'] in ('align','vent','seal','reseat_cable'):
            if self.power:return self.reject('Service requires power off.')
            op=args['operation']
            if op=='reseat_cable':self.loose=False;return {'ok':True,'operation':op}
            if not self.restricted:return self.reject('Airflow is already clear.')
            if op in self.progress:return self.reject('This operation is already complete.')
            if op=='align' and not self.job.align_first and 'vent' not in self.progress:return self.reject('Pressure prevents alignment.')
            if op=='vent' and self.job.align_first and 'align' not in self.progress:return self.reject('Alignment lock prevents venting.')
            if op=='seal' and not {'align','vent'}<=set(self.progress):return self.reject('Mechanical work is incomplete; sealing refused.')
            self.progress.append(op)
            if op=='seal':self.restricted=False
            return {'ok':True,'operation':op,'visible_work':list(self.progress)}
        if name=='calibrate' and set(args)=={'gain','bias'} and type(args['gain']) is int and type(args['bias']) is int and 1<=args['gain']<=4 and -20<=args['bias']<=20:
            if self.power:return self.reject('Calibration requires power off.')
            self.gain=args['gain'];self.bias=args['bias']
            return {'ok':True,'installed_gain':self.gain,'installed_bias':self.bias}
        if name=='test' and not args:
            accurate=all((self.job.gain*t+self.job.bias-self.bias)/self.gain==t for t in (30,70))
            self.passed=bool(self.power and accurate and self.temperature()<=60 and not self.loose and (not self.progress or 'seal' in self.progress))
            return {'pass':self.passed,'observation':'runs steadily under load' if self.passed else 'load certification did not pass'}
        return self.reject('Unknown tool or invalid arguments.')
    def snapshot(self):return self.inspect()
    def metrics(self):return {'measurements':self.measurements,'invalid_actions':self.invalid}

class ServiceDemo:
    live=False;name='observation-only scripted repair'
    def decide(self,c):
        xs=[decode(x) for x in c['current_job_log']]
        def act(n,**a):return Reply({'name':n,'arguments':a})
        if not xs:return act('inspect')
        initial=xs[0]['result'];scope={k:initial[k] for k in ('component','revision','origin')}
        probes={x['action']['arguments']['channel']:x['result'] for x in xs if x['action']['name']=='probe' and 'ok' not in x['result']}
        samples={x['result']['level']:x['result'] for x in xs if x['action']['name']=='sample_sensor' and 'level' in x['result']}
        remembered=None;prior=c['prior_memory']
        if isinstance(prior,dict):
            for r in prior.get('records',[]):
                if r['applicability']==scope:
                    try:
                        candidate=json.loads(r['text']).get('calibration')
                        if isinstance(candidate,dict):remembered=candidate
                    except (ValueError,AttributeError):pass
        else:
            identity=None;candidate=None
            for e in [decode(e) for e in prior]:
                if e['action']['name']=='inspect':
                    identity={k:e['result'].get(k) for k in scope}
                    candidate={'gain':e['result'].get('installed_gain'),'bias':e['result'].get('installed_bias')}
                if e['action']['name']=='calibrate' and e['result'].get('ok'):
                    candidate={'gain':e['result']['installed_gain'],'bias':e['result']['installed_bias']}
                if e['action']['name']=='test' and e['result'].get('pass') and identity==scope:remembered=candidate
        # If supplied evidence failed certification, fall back to observations, not an oracle.
        if any(x['action']['name']=='test' and not x['result'].get('pass') for x in xs):remembered=None
        for channel in ('thermal','continuity'):
            if channel not in probes:return act('probe',channel=channel)
        if probes['thermal']['airflow']=='restricted' and 'interlocks' not in probes:return act('probe',channel='interlocks')
        if remembered is None:
            for level in ('low','high'):
                if level not in samples:return act('sample_sensor',level=level)
            low,high=samples['low'],samples['high']
            gain=(high['raw_reading']-low['raw_reading'])//(high['reference_temperature']-low['reference_temperature'])
            remembered={'gain':gain,'bias':low['raw_reading']-gain*low['reference_temperature']}
        power=next((x['result']['power'] for x in reversed(xs) if 'power' in x['result']),'on')
        successful=[x for x in xs if x['result'].get('ok')]
        operations={x['action']['arguments'].get('operation') for x in successful}
        if probes['thermal']['airflow']=='restricted' and 'seal' not in operations:
            if power=='on':return act('power',state='off')
            order=('align','vent','seal') if probes['interlocks']['vent_interlock']!='clear' else ('vent','align','seal')
            return act('operate',operation=next(o for o in order if o not in operations))
        if probes['continuity']['continuity']=='intermittent' and 'reseat_cable' not in operations:
            if power=='on':return act('power',state='off')
            return act('operate',operation='reseat_cable')
        installed=next((x['result'] for x in reversed(xs) if x['action']['name']=='calibrate' and x['result'].get('ok')),initial)
        if installed['installed_gain']!=remembered['gain'] or installed['installed_bias']!=remembered['bias']:
            if power=='on':return act('power',state='off')
            return act('calibrate',**remembered)
        if power=='off':return act('power',state='on')
        return act('test')

def suite(variant='standard-v1'):
    if variant!='standard-v1':raise ValueError('Unknown variant.')
    jobs=(ServiceJob(1,'Amber','R1','factory',2,10,1,0),ServiceJob(2,'Amber','R1','factory',2,10,2,10),
          ServiceJob(3,'Amber','R1','factory',2,10,3,-8),ServiceJob(4,'Amber','R1','factory',2,10,2,10,restricted=True),
          ServiceJob(5,'Mint','R1','factory',2,10,1,5),ServiceJob(6,'Mint','R1','replacement',3,-5,1,0),
          ServiceJob(7,'Violet','R1','factory',2,10,4,0),ServiceJob(8,'Violet','R3','factory',4,-3,1,0,True,True,True))
    return TaskSuite('service-v1','Service transfer: eight tickets','Calibration, healthy units, physical faults, component transfer, replacement exceptions and novel compound service.',
        'service-v1:'+variant,jobs,TOOLS,INSTRUCTIONS,ServiceWorld,ServiceDemo,{'variant':variant,'jobs':[asdict(j) for j in jobs]})
