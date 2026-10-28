# Defining repair tasks

Read [the task contract](../../docs/TASK_DEFINITION_SPEC.md) first. `TaskSuite` is the runner’s integration point; fixture dataclasses make new jobs straightforward to add.

## Available sets

**baseline-v1** preserves the original ten tickets in `repair_shop/world.py`: inspection exposes faulty components, cooler work uses family/revision-specific sequences, some jobs repeat and some start partly repaired. This is the comparison baseline; do not alter it.

**diagnostic-v1** uses `DiagnosticJob` and `DiagnosticWorld` in `diagnostic.py`. Inspection reveals symptoms rather than a fault list. Each `diagnose` call measures one component. Electrical work needs power off, final testing needs power on, fuse replacement consumes a spare, and cooler interlocks vary by revision. Failed actions give physical observations rather than the next action to take.

| Job | Author-facing scenario | Evaluation purpose |
| --- | --- | --- |
| 1 | Amber R1 cooler | Learn pressure-before-alignment constraint |
| 2 | Mint R1 sensor | Diagnose a drifting sensor |
| 3 | Amber R1 cable | Same symptom, different fault |
| 4 | Amber R1 cooler | Reuse an earlier procedure |
| 5 | Mint R1 cooler + sensor | Combine two repairs and reverse cooler ordering |
| 6 | Mint R1 fuse + cable | Startup symptom hides a second fault |
| 7 | Amber R1 cooler + cable | Combine learned procedures |
| 8 | Mint R1 sensor | Delayed repeat across intervening jobs |
| 9 | Amber R2 cooler | Avoid applying an obsolete revision’s procedure |
| 10 | Amber R2 cooler + sensor, already tuned | Respect completed work and handle another fault |

This table is for task authors; it is not included in agent prompts. The public UI shows customer tickets and the suite description. Every job has a valid path within the default 12-step cap, verified by an observation-only demo policy. Models may still fail or choose a longer path; the demo is not a baseline AI competitor. Replacing a healthy fuse spends the spare but does not create a new fault in this version.

## Add fixtures within a new version

For a new diagnostic collection, reuse `DiagnosticJob`, `DiagnosticWorld`, tools and the demo, but give the suite a new versioned ID. Example fixture:

```python
DiagnosticJob(
    number=1, family='Amber', revision='R2',
    faults=('cooler', 'cable'), title='Revised cooler with loose cable',
    progress=(), spares=1,
)
```

Keep unique consecutive job numbers and valid component/operation names. Choose observable, solvable initial conditions; do not create an impossible resource budget accidentally. `title` is author metadata, not an agent hint. Add the suite to the explicit `SUITES` registry in `__init__.py`. The UI discovers registered suites and adjusts the available job count.

## Add a different world

1. Define an immutable ticket fixture with a public `ticket()` method.
2. Implement a fresh deterministic world and strict tool schemas. Validate tool inputs and keep hidden state private.
3. Define public instructions and an observation-only free demo policy.
4. Construct a `TaskSuite` with canonical `fixture_data` and a new ID.
5. Register it explicitly. Do not add dynamic import/eval or uploaded code execution.
6. Add tests for solvability, wrong actions, scarce resources, revision changes, hidden-state separation, deterministic replay and step limits. Run the full offline suite before requesting any paid test.

The current runner selects the first N tickets in registered order. It does not shuffle or sample them. To test a longer accumulating memory history, define a longer ordered suite; repeating a shift resets memory. Manuals are deferred; the contract describes the future retrieval interface.
