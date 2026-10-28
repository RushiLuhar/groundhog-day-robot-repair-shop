"""Original harder repair tasks: targeted diagnosis and conditional procedures, no manuals."""
from dataclasses import dataclass
from ..model import DemoModel, Reply

OPS=('power_off','power_on','vent','tune','seal','reseat_cable','replace_fuse','calibrate_sensor')
COMPONENTS=('cooler','cable','fuse','sensor')
TOOLS=tuple({'type':'function','name':name,'description':desc,'strict':True,
    'parameters':{'type':'object','properties':props,'required':list(props),'additionalProperties':False}}
    for name,desc,props in [
        ('inspect','Read the customer identity, symptoms, power state and visible work. Does not diagnose components.',{}),
        ('diagnose','Measure one component. Measurements can identify faults and physical constraints.',
         {'component':{'type':'string','enum':list(COMPONENTS)}}),
        ('operate','Perform one action. Vent releases cooler pressure; tune aligns its controller; seal closes it. Electrical work (cable, fuse, sensor) requires power off. Fuse replacement uses one spare. Power must be on to test.',
         {'operation':{'type':'string','enum':list(OPS)}}),
        ('test','Run the robot under load. Returns pass or observable symptoms, not a list of faulty parts.',{})])
INSTRUCTIONS='''This workshop has targeted component diagnostics. Inspect gives symptoms, not a complete diagnosis.
Use diagnose to choose repairs. Cooler work may have physical interlocks; remeasure after an unsuccessful action.
Electrical work requires power off; tests require power on. The displayed spare count is a real resource limit.
Robot family and hardware revision can change cooler behavior. Earlier memories may not apply to this revision.
You have no manual in this task set. Every task is solvable from tool observations alone.'''


@dataclass(frozen=True)
class DiagnosticJob:
    number: int
    family: str
    revision: str
    faults: tuple[str,...]
    title: str
    progress: tuple[str,...] = ()
    spares: int = 1

    def ticket(self):
        return {'job':self.number,'customer':f'{self.family} {self.revision}',
                'complaint':'will not start' if 'fuse' in self.faults else 'stutters and stops under load'}


JOBS=(
    DiagnosticJob(1,'Amber','R1',('cooler',),'Unstable cooling'),
    DiagnosticJob(2,'Mint','R1',('sensor',),'A misleading temperature reading'),
    DiagnosticJob(3,'Amber','R1',('cable',),'Similar symptom, another cause'),
    DiagnosticJob(4,'Amber','R1',('cooler',),'First repeat'),
    DiagnosticJob(5,'Mint','R1',('cooler','sensor'),'Two interacting symptoms'),
    DiagnosticJob(6,'Mint','R1',('fuse','cable'),'Startup failure with a second fault'),
    DiagnosticJob(7,'Amber','R1',('cooler','cable'),'A compound repair'),
    DiagnosticJob(8,'Mint','R1',('sensor',),'Delayed repeat'),
    DiagnosticJob(9,'Amber','R2',('cooler',),'Revised cooler interlock'),
    DiagnosticJob(10,'Amber','R2',('cooler','sensor'),'Revised cooler plus sensor',progress=('tune',)),
)


class DiagnosticWorld:
    def __init__(self,job):
        self.job=job; self.passed=False; self.power=True
        self.fixed=set(); self.progress=list(job.progress); self.spares=job.spares
        self.invalid_actions=0; self.diagnostic_calls=0; self.parts_used=0

    def unresolved(self,component):
        return component in self.job.faults and (('seal' not in self.progress) if component=='cooler' else component not in self.fixed)

    def inspect(self):
        return {**self.job.ticket(),'power':'on' if self.power else 'off',
                'visible_work':list(self.progress),'spare_fuses':self.spares}

    def diagnose(self,component):
        self.diagnostic_calls+=1
        if component=='cooler':
            fault=self.unresolved('cooler')
            locked=fault and (self.job.family,self.job.revision)!=('Amber','R1') and 'tune' not in self.progress
            return {'component':component,'pressure':'high' if fault and 'vent' not in self.progress else 'normal',
                    'controller':'misaligned' if fault and 'tune' not in self.progress else 'aligned',
                    'release_valve':'locked' if locked else 'available',
                    'tuning_interlock':'pressure prevents adjustment' if fault and (self.job.family,self.job.revision)==('Amber','R1') and 'vent' not in self.progress else 'clear',
                    'housing':'open' if fault else 'sealed'}
        return {'component':component,'reading':(
            {'cable':'intermittent continuity','fuse':'open circuit','sensor':'signal drifts'}[component]
            if self.unresolved(component) else
            {'cable':'steady continuity','fuse':'closed circuit','sensor':'signal stable'}[component])}

    def reject(self,message):
        self.invalid_actions+=1
        return {'ok':False,'observation':message}

    def call(self,name,arguments):
        if not isinstance(arguments,dict): return self.reject('Invalid arguments.')
        if name=='inspect' and not arguments: return self.inspect()
        if name=='diagnose' and set(arguments)=={'component'} and arguments['component'] in COMPONENTS:
            return self.diagnose(arguments['component'])
        if name=='test' and not arguments:
            remaining=any(self.unresolved(c) for c in COMPONENTS)
            self.passed=self.power and not remaining
            return {'pass':self.passed,'observation':'runs steadily under load' if self.passed else
                    'power is off' if not self.power else 'will not start' if self.unresolved('fuse') else 'stutters and stops under load'}
        if name!='operate' or set(arguments)!={'operation'} or arguments['operation'] not in OPS:
            return self.reject('Unknown action or invalid arguments.')
        op=arguments['operation']
        if op in ('power_off','power_on'):
            self.power=op=='power_on'
            return {'ok':True,'power':'on' if self.power else 'off'}
        if op in ('reseat_cable','replace_fuse','calibrate_sensor'):
            if self.power: return self.reject('Electrical service interlock: supply is live.')
            component={'reseat_cable':'cable','replace_fuse':'fuse','calibrate_sensor':'sensor'}[op]
            if op=='replace_fuse':
                if self.spares==0: return self.reject('No spare fuse remains.')
                self.spares-=1; self.parts_used+=1
            self.fixed.add(component)
            return {'ok':True,'operation':op,'spare_fuses':self.spares}
        readings=self.diagnose('cooler'); self.diagnostic_calls-=1  # Internal check is not a diagnostic tool call.
        if not self.unresolved('cooler'): return self.reject('Cooler readings are already normal.')
        if op in self.progress: return self.reject('No change: this adjustment is already complete.')
        if op=='vent' and readings['release_valve']=='locked': return self.reject('Release valve stays locked; pressure unchanged.')
        if op=='tune' and readings['tuning_interlock']!='clear': return self.reject('Adjustment is blocked by pressure; alignment unchanged.')
        if op=='seal' and not {'vent','tune'}<=set(self.progress): return self.reject('Housing will not latch; cooler readings remain unstable.')
        self.progress.append(op)
        return {'ok':True,'operation':op,'visible_work':list(self.progress)}

    def snapshot(self): return self.inspect()  # No hidden faults, recipes or oracle.

    def metrics(self):
        return {'diagnostic_calls':self.diagnostic_calls,'invalid_actions':self.invalid_actions,'parts_used':self.parts_used}


class DiagnosticDemo(DemoModel):
    """An observation-only demonstration policy, never an AI score or oracle feed."""
    def decide(self,c):
        xs=c['current_job_exchanges']
        def act(name,**arguments): return Reply({'name':name,'arguments':arguments})
        if not xs: return act('inspect')
        readings={x['action']['arguments']['component']:x['result'] for x in xs if x['action']['name']=='diagnose'}
        for component in COMPONENTS:
            if component not in readings: return act('diagnose',component=component)
        success=[x['action']['arguments'].get('operation') for x in xs if x['result'].get('ok')]
        power=next((x['result']['power'] for x in reversed(xs) if 'power' in x['result']),'on')
        cooler=readings['cooler']; complete=set(xs[0]['result'].get('visible_work',[]))|set(success)
        if cooler['housing']=='open' and 'seal' not in complete:
            order=('tune','vent','seal') if cooler['release_valve']=='locked' else ('vent','tune','seal')
            return act('operate',operation=next(op for op in order if op not in complete))
        for component,reading,op in [('cable','intermittent continuity','reseat_cable'),('fuse','open circuit','replace_fuse'),('sensor','signal drifts','calibrate_sensor')]:
            if readings[component]['reading']==reading and op not in success:
                if power=='on': return act('operate',operation='power_off')
                return act('operate',operation=op)
        if power=='off': return act('operate',operation='power_on')
        return act('test')
