# Budget-only live evaluation: 50,000 tokens per job

The larger allowance let the cooling repairs finish, but it did not make structured memory more useful. All 72 scheduled attempts completed their execution: **65 certified, seven unfinished, zero interrupted/unattempted**. No API, logger or writer errors occurred. The six compound attempts with memory exhausted the job allowance; one no-memory replacement attempt ended on response truncation after avoidable actions.

This is a second stochastic run of one fixed eight-ticket world, not a causal estimate of the budget change or a general memory ranking. Later prompt/task revisions are **not represented in these live results**.

## Protocol and reproducibility

Frozen, clean source: `fc35987a61683f7c9c701fee324f707c8d7f58fc`. Compared with [the preceding run](LIVE_EVALUATION_2026-10-28.md), only the experiment name and three budget controls changed: **50,000 combined repair/writer input + output tokens per job**, **2,000,000 run tokens**, and **$0.50 estimated run spend**. Per-job checks use returned usage and can exceed the allowance by one returned call. Conservative run admission remained active; no reservation was exceeded.

All other controls were preserved: `service-v1` / `standard-v1`; three fresh repetitions of eight ordered tickets; none/rolling/structured memory; rotated condition order; `gpt-6-luna`, medium reasoning, 2,048 output tokens for both roles; 20 tool actions/job; rolling 40 entries, 3,000 retained tokens, 2,000 supplied tokens. Prompts remained `repair-objective-v1` and `job-end-writer-v1`, and all logs/policies/tools were unchanged. The writer ran once at job end when allowance remained. No retry, model substitution, top-up or deterministic demo policy was used.

Reproduction records:

- [Exact configuration](../examples/evaluation-live-2026-10-28-50k.json)
- [Frozen manifest and all aggregates](evaluation-results/2026-10-28-50k/summary.json)
- [All 72 attempts, with role input/output tokens and elapsed time](evaluation-results/2026-10-28-50k/attempts.csv)
- [Chart-ready comparison with explicit matched denominators](evaluation-results/budget-comparison/comparison.json)
- [144 rows spanning both runs, including unattempted rows](evaluation-results/budget-comparison/paired-attempts.csv)

These files contain synthetic aggregate data and public configuration only. Raw transcripts, database files, API identifiers, credentials and local paths are excluded. The live configurations record historical authorization, not standing permission for another paid run.

## Complete 50k run

Each condition attempted the same 24 tickets: eight tickets across three fresh shifts. All failures remain in the denominators. Elapsed time includes local runner/persistence overhead and is not a model-only latency measurement.

| Memory | Certified | Unfinished | Steps | Repair tokens | Writer tokens | Total tokens | Estimated USD | Attempt seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| None | 23/24 | 1 | 253 | 448,267 | 0 | 448,267 | 0.0588871 | 630.12 |
| Rolling | 21/24 | 3 | 215 | 692,168 | 0 | 692,168 | 0.0797424 | 484.91 |
| Structured | 21/24 | 3 | 232 | 672,896 | 109,301 | 782,197 | 0.0954169 | 628.86 |

Fewer steps cannot be read as greater efficiency when the final repair was unfinished. Structured writer overhead was 109,301 tokens, **14.0%** of that condition's total; supplying notes on repair requests adds further input usage. Deterministic logs made no model calls.

| Shift | None | Rolling | Structured |
| --- | --- | --- | --- |
| 1 | 7/8 certified; 86 steps | 7/8; 70 steps | 7/8; 77 steps |
| 2 | 8/8; 82 steps | 7/8; 74 steps | 7/8; 76 steps |
| 3 | 8/8; 85 steps | 7/8; 71 steps | 7/8; 79 steps |

Per-ticket step counts below are shift 1 / shift 2 / shift 3. `U` marks unfinished. The CSV provides exact per-ticket token, role, cost and time values.

| Ticket | None | Rolling | Structured |
| --- | --- | --- | --- |
| 1 — discovery | 9 / 9 / 9 | 9 / 9 / 9 | 9 / 8 / 9 |
| 2 — healthy | 7 / 6 / 6 | 4 / 4 / 4 | 6 / 10 / 6 |
| 3 — repeat with different settings | 9 / 13 / 11 | 7 / 9 / 7 | 9 / 8 / 9 |
| 4 — cooling fault | 12 / 11 / 14 | 10 / 10 / 9 | 13 / 12 / 14 |
| 5 — transfer | 8 / 9 / 9 | 9 / 9 / 9 | 9 / 8 / 9 |
| 6 — replacement | 17 U / 9 / 9 | 9 / 9 / 9 | 9 / 9 / 10 |
| 7 — factory return | 9 / 8 / 9 | 9 / 11 / 11 | 9 / 8 / 9 |
| 8 — compound | 15 / 17 / 18 | 13 U / 13 U / 13 U | 13 U / 13 U / 13 U |

## Compare equal exposure across budgets

The earlier run stopped globally, so compare only its complete paired groups: shift 1 tickets 1–8 and shift 2 tickets 1–7, **15 attempts per condition in each run**. The new run's additional nine ticket groups are not included in this table.

| Memory | Certified, 30k → 50k | Steps, 30k → 50k | Tokens, 30k → 50k | Estimated USD, 30k → 50k |
| --- | --- | --- | --- | --- |
| None | 14/15 → 14/15 | 141 → 151 | 227,353 → 263,034 | 0.0290501 → 0.0354134 |
| Rolling | 13/15 → 14/15 | 121 → 131 | 367,678 → 413,244 | 0.0419442 → 0.0476812 |
| Structured | 12/15 → 14/15 | 133 → 140 | 375,554 → 461,849 | 0.0453910 → 0.0570765 |

All nine cooling attempts passed in the new run. Structured cooling consumed 43,619 / 39,117 / 47,806 total tokens including maintenance. But the no-memory failure moved from the first compound ticket to the first replacement ticket. Changed remaining-budget context and stochastic trajectories prevent attributing every outcome difference to the allowance alone.

## Trace findings and the resulting changes

**Evidence supplied was not evidence used.** Structured memory sampled twice on every ticket in all three shifts. Rolling sampled zero times on the healthy, early-repeat and cooling tickets in every shift, and twice elsewhere. Its repeat trajectories are consistent with reuse, even when extra probes erased some step savings. All policies remeasured transfer and factory-return cases. Replacement-origin notes were retained and supplied alongside factory notes, but successful remeasurement does not demonstrate that those notes caused correct exception handling.

**Narratives grew rather than converging into compact facts.** The writer accepted 12 records per shift; final stores contained ten or eleven episodic/procedural records and no semantic records. There were zero rejected candidates and five retention evictions across the three shifts. Retention reached 2,841–2,937 tokens; supplied contexts approached the 2,000-token ceiling. Case-specific caveats, paraphrased procedures and overlapping citation lists accumulated. The writer still lacked the public transfer rule supplied to repair. The later `job-end-writer-v2` contract therefore supplies the same public rules, requests concise scoped relationships, minimal sufficient citations and omission of unchanged facts. This is a hypothesis to test, not a measured improvement.

**Constraints were mistaken for faults.** On shift-one replacement ticket 6, no memory correctly installed gain 3 / bias -5, then probed interlocks, attempted vent and align despite clear airflow, tested with power off, and repeated checks until a 2,048-token response truncated. Structured memory also attempted an unnecessary vent on a healthy unit in shift two. The later common repair prompt distinguishes operation preconditions from evidence that service is needed, tracks current power, and prioritizes unresolved faults and final certification.

**The compound failures were real incomplete repairs.** Both memory policies stopped at 13 actions in every shift, at 50,184–51,435 returned tokens. Some still needed cable service or calibration; one rolling attempt had completed physical work and powered on but had no remaining request for its test. One structured attempt had a failed test and then rechecked thermal state while the cable fault remained. No memory completed all three in 15–18 actions; two required recovery after a failed test exposed an unresolved fault. None of the unfinished attempts was promoted to success.

The new `service-v2` prototype adds a cable fault to the early calibration repeat, makes the factory-return unit start with the replacement's settings, and gives the novel compound unit a normal-looking indication despite actual overheating. It also makes the public power-on precondition explicit in test feedback. This exercises diagnostic transfer and exceptions while preserving cold solvability and independent certification. It does not enlarge the sequence or tune a window to force one memory policy to win. See [the versioned tuning record](EVALUATION_TUNING_V2.md) for implementation and offline evidence.

## Accounting and limits

Execution took **1,745.00 seconds (29.08 minutes)**. All **722 calls** returned known usage: 701 repair calls (including the truncated response) and 21 writers. There were 700 executed tool actions. Repair reported 1,726,222 input + 87,109 output tokens; writers reported 91,952 input + 17,349 output. Total: **1,922,632 tokens**, **$0.2340464 estimated**, zero unknown calls, zero infrastructure errors, one incomplete response. All returned models were `gpt-6-luna`, tier `default`.

Pricing uses the same [pinned official Luna standard rates](https://developers.openai.com/api/docs/models/gpt-6-luna), checked October 28: $0.10/M input and $0.50/M output. The largest request input was 7,665 tokens, below the long-context threshold. Cache discounts, cache-write premiums, regional adjustments and taxes are excluded; this is not a bill. No post-tuning results are included in these measurements; see the separate [subsequently authorized combined follow-up](LIVE_EVALUATION_TUNED_2026-10-28.md).

This remains three repetitions of one deterministic fixture set, not broad statistical evidence. The model identifier is an alias, and elapsed time includes local overhead. At this run's initial delivery, the prompt/task changes had only offline/free-browser checks. The later combined follow-up is reported separately, with its own frozen versions and limits.
