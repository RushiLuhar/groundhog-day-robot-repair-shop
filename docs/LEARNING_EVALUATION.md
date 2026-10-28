# Testing whether memory earns its cost

The `learning-v1` suite adds 32 ordered jobs. It tests a mechanism the older suites barely exercised: spend tool calls to learn a reusable calibration, then decide when that evidence applies to a later unit. The baseline and diagnostic suites remain unchanged and selectable.

## What changed

1. **Memory retention is explicit and observable.** New configurations default to `merge_v2` for structured memory. Each candidate record is validated independently against observed job IDs and robot revisions. One invalid citation does not discard valid sibling records. Omitting an old record does not delete it. A deterministic token budget still limits memory; removals and rejected records are recorded.
2. **The sequence has repeated learning opportunities.** Three factory families recur immediately and after delays. Later jobs revisit earlier revisions and combine calibration with cable work. Memories reset only between shifts, not between jobs.
3. **Discovery costs steps and can be reused.** Each axis requires a separate measurement. A signed error plus the current value identifies the required setting. A remembered factory calibration can avoid those three measurement calls, subject to testing. Every agent has the same tools and observations; no agent receives the solution as privileged state.
4. **Exceptions and controls prevent a guaranteed memory win.** New revisions change calibration values. Marked replacement modules invalidate factory assumptions. Returning to a factory unit requires keeping that exception separate. Cable-only control jobs start correctly calibrated, so calibration memory offers no repair advantage.

## Sequence

| Jobs | Purpose |
| --- | --- |
| 1–3 | Discover Amber R1, Mint R1 and Violet R1 calibrations |
| 4, 6–7 | Early revisits across intervening jobs |
| 8 | Immediate Violet repeat, within a short notebook window |
| 9, 11, 14, 23, 29, 32 | Delayed repeats |
| 10, 21 | Reuse calibration while also repairing a cable |
| 13, 20, 28 | First exposure to a new revision |
| 17, 22, 30 | Repeat the new revision |
| 15, 25 | Explicitly marked replacement-module exceptions |
| 16, 26 | Return to an older revision |
| 19, 27 | Return from a replacement module to factory calibration |
| 5, 12, 18, 24, 31 | Cable-only controls |

The first N jobs are selected in order. Choose all 32 to include every phase. Repeated shifts start empty; they do not extend the learning history. Phase labels and hidden calibration fixtures are evaluation metadata, never inserted into model prompts.

A cold factory calibration has an observation-based eight-step path: inspect, measure three axes, power off, apply calibration, power on, test. Correct remembered calibration can reduce this to five. Compound cable work adds one action. Controls take five actions. These are demonstrated paths, not promised model behavior or optimality claims.

## Memory audit

Each attempt reports:

- Earlier jobs with the same robot family/revision.
- Source job IDs and structured record IDs actually supplied as prior memory.
- Matching earlier jobs absent from that input.
- Accepted candidate IDs, rejected record locations/reasons, retained records, removed prior IDs and budget exclusions after maintenance.
- Exact notes/exchanges supplied and kept, accessible in the mechanic drawers.

A newer citation may supersede an older citation without losing the underlying fact. Matching family/revision is only a proxy for a learning opportunity. A replacement module can share that identity while requiring different calibration. “Supplied” does not prove that the model used evidence, used it correctly or benefited from it. Citation validation checks structure, observed sources and claimed pass support; it does not prove every sentence is entailed by the observations. No hidden answer key validates generated notes.

`merge_v2` retains distinct validated statements and replaces exact duplicate statements with their newer citation. To fit the budget it considers newest evidence first, prioritizing procedural, semantic, then episodic records for equal source age; record hashes break remaining ties. It may retain contradictory statements and may evict a useful older fact. Both are visible evaluation outcomes. It does not know future jobs, consult hidden fixtures, add solution facts, or make a second model call.

The maintenance model receives a catalog of this bay’s observed tickets and pass outcomes, alongside the current exchanges and previous notes. Those input tokens count toward usage. The repair model receives only the configured prior notes or notebook, current ticket and current exchanges.

## Reproducibility and compatibility

Existing saved configurations without `memory_update_policy` load as `replace_v1`, preserving the original whole-note replacement behavior. Existing rows and results are not rewritten. New configurations use `merge_v2`; choose it explicitly in a loaded legacy configuration and save a new version to compare the retention change. Reports persist the selected policy and memory implementation marker.

The graph still uses separate checkpoint threads for each run/repetition/bay/job and separate stores per run/repetition/bay. SQLite persists experiment snapshots and reports; it does not resume an interrupted paid graph.

## Suggested experiments

Start with the free demo to verify controls and audit drawers. Its observation-based script illustrates possible savings and safe exception handling; it is not an AI evaluation and its zero-token results do not estimate OpenAI cost.

For a later authorized live evaluation, keep model, reasoning and task order fixed. First compare memory policies over all 32 jobs with equal step/output limits. Separately vary notebook size or structured-note budget. Compare discovery, immediate/delayed repeats, exceptions, revisions and controls; inspect passes alongside steps and total tokens including memory writes. Preserve the original 12-step/1,024-output configuration as a reference when exploring larger limits.

A low-cost failure is not a win. Higher pass rates with extra tokens may still be useful. Report unfinished reasons separately: tool-step limit, response output limit when explicitly reported by the API, missing/invalid tool action, user stop or API failure. No statistical significance or model ranking is inferred from a few runs.

## Validation

Offline tests exercise the full 32-job schedule for all three policies across two fresh-memory shifts (192 attempts), including immediate raw-notebook reuse, delayed structured reuse, revision separation, exception handling and identical control costs. Tests also cover partial note rejection, deterministic budget eviction, source catalogs, old-version loading and API output-limit classification using mocked responses. This release has made no new paid model calls.

Official sources checked 2026-10-28: [LangGraph persistence](https://docs.langchain.com/oss/python/langgraph/persistence). The OpenAI Responses reference page was too large for the browser reader; output-limit parsing was checked against the installed official SDK types and mocked responses. These sources describe API primitives; the task design and retention policy are project choices.
