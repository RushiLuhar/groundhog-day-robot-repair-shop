"""Explicit task registry. No uploaded code, dynamic imports or private manuals."""
from dataclasses import asdict
from .base import TaskSuite
from ..world import World, JOBS, SEED
from ..model import TOOLS, DemoModel
from .diagnostic import DiagnosticWorld, DiagnosticDemo, JOBS as DIAGNOSTIC_JOBS, TOOLS as DIAGNOSTIC_TOOLS, INSTRUCTIONS

BASELINE=TaskSuite('baseline-v1','Baseline: ten original repairs',
    'Original fully observable diagnostics, two cooler sequences, repeats and revision changes. Unchanged for comparison.',
    SEED,JOBS,tuple(TOOLS),'',World,DemoModel,{'jobs':[asdict(j) for j in JOBS]})
DIAGNOSTIC=TaskSuite('diagnostic-v1','Challenge: diagnose before repairing',
    'Targeted measurements, overlapping symptoms, power interlocks, limited spare fuses, compound faults and revision-specific cooler behavior. No manuals.',
    'diagnostic-world-v1:20261028',DIAGNOSTIC_JOBS,DIAGNOSTIC_TOOLS,INSTRUCTIONS,
    DiagnosticWorld,DiagnosticDemo,{'jobs':[asdict(j) for j in DIAGNOSTIC_JOBS]})
from .learning import LearningWorld, LearningDemo, JOBS as LEARNING_JOBS, TOOLS as LEARNING_TOOLS, INSTRUCTIONS as LEARNING_INSTRUCTIONS
LEARNING=TaskSuite('learning-v1','Learning: 32 repairs with delayed repeats',
    'Learn reusable calibrations through three separate measurements. Revisit families after delays, handle revision changes and marked replacement modules, and compare cable-only controls where calibration memory adds no benefit.',
    'learning-world-v1:20261028',LEARNING_JOBS,LEARNING_TOOLS,LEARNING_INSTRUCTIONS,
    LearningWorld,LearningDemo,{'jobs':[asdict(j) for j in LEARNING_JOBS]})
SUITES={s.id:s for s in (BASELINE,DIAGNOSTIC,LEARNING)}

def get_suite(identifier):
    if identifier not in SUITES: raise ValueError(f'Unknown task set: {identifier}')
    return SUITES[identifier]


# New condition-based runner: explicit trusted registry, separate from legacy bay adapters.
from ..evaluation.service import suite as service_suite
from ..evaluation.service_v2 import suite as service_suite_v2
EVALUATION_SUITES={'service-v1':service_suite,'service-v2':service_suite_v2}

def get_evaluation_suite(identifier,variant='standard-v1'):
    if identifier not in EVALUATION_SUITES:raise ValueError('Unknown evaluation task set.')
    return EVALUATION_SUITES[identifier](variant)
