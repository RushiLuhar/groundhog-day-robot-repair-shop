"""Versioned diagnostic counterexamples; service-v1 remains frozen."""
from dataclasses import asdict,replace
from ..tasks.base import TaskSuite
from .service import ServiceWorld,ServiceDemo,TOOLS,INSTRUCTIONS,suite as original_suite

PUBLIC_RULES=INSTRUCTIONS+'''
An interlock describes whether an operation is permitted, not whether cooling service is needed. Clear airflow does not require vent/align/seal. Completed mechanical work means sealing work that was actually started; an untouched healthy cooler needs no work.
A normal-looking indicated temperature is not independent evidence of thermal safety. Calibration and a separate physical fault can coexist. The latest power observation determines whether a test can run; a power-off test reports that unmet public precondition.'''

class ServiceWorldV2(ServiceWorld):
    def call(self,name,args):
        if name=='test' and args=={} and not self.power:
            self.passed=False
            return {'pass':False,'observation':'Load certification requires power on; no powered test was performed.'}
        return super().call(name,args)

def suite(variant='standard-v1'):
    if variant!='standard-v1':raise ValueError('Unknown variant.')
    jobs=list(original_suite().jobs)
    # A repeat is not permission to replay a whole repair: there is a second fault.
    jobs[2]=replace(jobs[2],loose=True)
    # Factory identity returns, but installed values resemble the replacement.
    jobs[6]=replace(jobs[6],initial_gain=3,initial_bias=-5)
    # True heat is 80; incorrect installed gain makes the indication look like 40.
    jobs[7]=replace(jobs[7],gain=2,bias=-12,initial_gain=4,initial_bias=-12)
    return TaskSuite('service-v2','Service decisions: scoped evidence and counterexamples',
        'Repeat plus an independent fault, transfer and origin exceptions, and compound service with a misleading indication. Unvalidated live.',
        'service-v2:'+variant,tuple(jobs),TOOLS,PUBLIC_RULES,ServiceWorldV2,ServiceDemo,
        {'variant':variant,'jobs':[asdict(j) for j in jobs]},implementation_version='2')
