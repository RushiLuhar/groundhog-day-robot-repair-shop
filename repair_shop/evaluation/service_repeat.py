"""Two fresh instances of one existing repair; no repeat hint enters agent context."""
from dataclasses import asdict, replace
from ..tasks.base import TaskSuite
from .service_v2 import suite as service_suite


def suite(variant='standard-v1'):
    base=service_suite(variant)
    first=base.jobs[0]
    jobs=(first,replace(first,number=2))
    return TaskSuite('service-repeat-v1','Exact repeat: two identical calibration repairs',
        'The same starting machine state twice, with independent certification and memory retained only within each pair.',
        'service-repeat-v1:'+variant,jobs,base.tools,base.instructions,base.create_world,base.create_demo,
        {'variant':variant,'jobs':[asdict(j) for j in jobs]})
