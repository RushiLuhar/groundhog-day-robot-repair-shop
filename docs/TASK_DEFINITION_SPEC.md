# Task definition contract — version 1

The harness compares agents on the same deterministic repair jobs. A task set owns its world, tools and scoring. The runner owns models, memory, limits, repetitions and accounting. This separation allows new problems without rewriting the agent loop.

## Units and identity

- **Task set:** a named, versioned ordered collection of jobs, such as `baseline-v1`.
- **Job:** one repair ticket plus private initial state. Its integer number is unique within a set.
- **Attempt:** one mechanic’s fresh world for one job. The identity is `(run_id, repetition, bay_id, job_number)`.
- **Step:** one tool call, including inspection, diagnosis, a rejected action or a test.
- **Shift:** all selected jobs across all three mechanics, in the same order.
- **Repetition:** another shift with fresh memories and worlds. Repetitions do not extend a memory history.

Each mechanic gets exactly one attempt per selected job per repetition. Models may choose different actions, but receive the same tools, task instructions and starting ticket. No hidden retry or automatic resume is allowed.

## Python interface

`repair_shop.tasks.base` defines `TaskTicket`, `TaskWorld` and the immutable `TaskSuite` dataclass. A suite provides:

| Field | Purpose |
| --- | --- |
| `id`, `title`, `description` | Stable versioned identity and readable task details |
| `seed` | Stable scenario seed/identifier; random generation must use a private seeded RNG |
| `jobs` | Ordered immutable ticket fixtures |
| `tools` | Official Responses API function schemas, strict objects with required fields |
| `instructions` | Public rules available equally to every mechanic |
| `create_world(job)` | A fresh independent world for each attempt |
| `create_demo()` | Observation-only scripted policy for free testing |
| `fixture_data` | Canonical, JSON-serializable initial state used for fingerprinting |
| `implementation_version` | Increment whenever world/scoring/demo semantics change |

A ticket exposes `number` and `ticket() -> dict`. Public tickets contain `job` and `customer`. The current structured-memory adapter expects `customer` to identify family and revision, e.g. `Amber R2`; records cite those fields and source job numbers. Non-repair tasks will need an explicit memory adapter before dropping that convention.

A world exposes `passed`, `call(name, arguments) -> dict`, and `snapshot() -> dict`. Optional `metrics() -> dict` returns aggregate evaluation counters. All outputs must be JSON-serializable. Unknown/malformed actions must return a bounded, public rejection, never execute arbitrary code. A failed or rejected tool call still consumes a step.

`passed` becomes true only after a successful explicit `test`. Finishing text is not proof of success. Reaching the step cap records unfinished, including a reason and the actual step count. The world cannot choose a model, make network calls, bill tokens or write cross-job memory.

## Public observations and hidden state

Private fixtures may contain faults, repair preconditions, scoring rules and resource counts. Keep hidden faults and solution sequences out of `ticket()`, tool responses, `snapshot()`, event logs and model context. Deliberate public diagnostics must be specified: baseline inspection reveals component faults; the challenge set requires targeted measurements.

A free demo must act only on the same current ticket and observations an agent receives. It cannot inspect world internals or use private fixture IDs as a solution lookup. Tests may inspect hidden state to verify scoring, but that state must not be sent to the model. Registry code is trusted local project code, not a sandbox for uploaded Python.

## Reproducibility and persistence

The suite fingerprint hashes its ID, seed, implementation version, canonical fixtures, tools and public instructions. It is a semantic version checksum, not a hash of Python source. Change the suite ID/version for incompatible behavior and bump implementation version for semantic changes; never silently replace a baseline. Preserve old suite registrations when comparing old configurations.

SQLite stores append-only configuration versions and immutable configuration/task snapshots at run start. Reports include the task ID, fingerprint, seed, per-mechanic settings, repetition, results and known usage. Returned API usage is checkpointed before another call; events/results are checkpointed at attempt completion. A process failure during a request may leave unknown usage. Never infer success, zero usage or safe retry from an incomplete checkpoint.

## Scoring and comparison

Report passes and unfinished attempts, tool steps, diagnostic calls, invalid actions, parts used, repair tokens, memory tokens and estimated dollars when pricing is known. Input/output counts must come from API responses; demo usage is zero and explicitly labeled scripted. Memory writes count in cost. Output limits include reasoning tokens, so a low cap can produce incomplete responses.

Keep effectiveness and efficiency separate. A low token count can reflect failure or weaker memory, not superior performance. Compare the same set and fingerprint, job count and repetition count. Changing several mechanic settings at once is exploratory and does not isolate a cause. This release does not compute confidence intervals or claim benchmark rankings.

## Deferred manual tasks

A future suite may supply original or authorized documents through explicit `search_manual` / `read_manual` tools. Treat document IDs and versions as fixtures included in the fingerprint. Retrieval consumes a step; retrieved text enters subsequent model input and is therefore counted by the API. All mechanics receive identical document access. Specify truncation, retrieval budgets, citation checks and contradictory revision handling before implementation. Do not preload hidden solutions into persistent memory. Private course PDFs, slides and notes must not be published.

Manual tools, arbitrary user-uploaded task code, variable bay counts, cross-run memory and automatic task generation are not implemented in version 1.
