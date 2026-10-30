# Sol comparison after the authorized spend extension

Across 72 scheduled positions, **68 repairs certified, three remained unfinished at the job-token allowance, and one retained the earlier spend interruption**. None were unattempted. Combined usage was **1,807,233 tokens and $3.765312 estimated**, below the unchanged 2M-token limit and the explicitly increased **$10 total** ceiling.

With Sol repairing and Luna writing memory, structured memory certified **24/24**, matching no cross-job memory with **30 fewer tool actions** (204 versus 234). It still used **38.8% more tokens and cost 17.8% more**. Rolling history again failed all three compound tickets at the job allowance. A stronger repair model did not eliminate context cost.

## What changed, and what was preserved

Repair used **`gpt-6-sol`**, the corresponding GPT-6 generation to the baseline's `gpt-6-luna`; the writer stayed **`gpt-6-luna`**. Official [Sol](https://developers.openai.com/api/docs/models/gpt-6-sol) and [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) model pages were checked October 29, and the authenticated model lookup confirmed Sol availability. Standard input/output rates were $2/$10 per million for Sol and $0.10/$0.50 for Luna. These are estimated standard-rate costs, not invoices; cache, regional/tier adjustments and taxes are excluded.

All task, prompt, reasoning, role, output, memory and job controls stayed fixed against the [tuned Luna run](LIVE_EVALUATION_TUNED_2026-10-28.md):

- `service-v2 / standard-v1`, eight ordered tickets, three memory conditions, three fresh shifts with rotated condition order.
- `repair-objective-v3`, `job-end-writer-v2`; medium reasoning and 2,048 output caps for both roles; 20 tool actions/job.
- 40 rolling entries, 3,000 retained memory tokens, 2,000 supplied tokens; factual deterministic logs and the same current-job context.
- 50,000 reported input + output tokens/job **including the writer**, and 2M combined run tokens. No retries, model substitution, hidden-answer access or post-result prompt/task tuning.

The whole-run dollar ceiling changed transparently. The [original $0.50 segment](LIVE_EVALUATION_SOL_2026-10-29.md), frozen at `e2e31c1be151cd5f14114ea4254dfc533e7f695d`, had already stopped after 11 started positions, 91 returned calls, 207,804 tokens and $0.4415131. The owner then authorized **$10 total, including that spend**.

The continuation source was **`f18a9b8ede78374f1c1a9dc292418328ce633616`**, clean after **120 offline tests passed**. A narrow explicit continuation restored memories by replaying recorded observations and writer merges, carried every prior call/charge, and executed only the **61 unattempted positions**. It did not retry or resume the interrupted rolling shift-1/ticket-4 repair. That position remains interrupted. A new linked manifest preserves the original manifest and report fingerprint; the old database/export and published partial result remain unchanged. This is not automatic crash recovery or a fresh replacement experiment.

The budget pause matters analytically: rolling shift-1 tickets 5–8 inherited a history without ticket 4's passing test. The comparison data flag those four positions and provide a sensitivity subset excluding them. Shifts 2 and 3 began with fresh memory as planned. The larger USD ceiling did not bind after continuation; the 2M-token and job allowances were unchanged. Luna retained its original $0.50 ceiling, which did not bind in that completed run.

## Results, including all non-success work

| Memory | Certified / 24 | Job-cap unfinished | Interrupted | Steps | Repair input | Repair output | Writer input | Writer output | Total tokens | Estimated USD | Attempt seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| None | 24 | 0 | 0 | 234 | 456,741 | 13,491 | 0 | 0 | 470,232 | 1.048392 | 363.32 |
| Rolling | 20 | 3 | 1 | 197 | 670,387 | 14,099 | 0 | 0 | 684,486 | 1.481764 | 328.24 |
| Structured | 24 | 0 | 0 | 204 | 544,860 | 12,959 | 78,755 | 15,941 | 652,515 | 1.235156 | 494.29 |

Structured's repair and writer totals were **557,819 and 94,696 tokens**. The writer cost $0.015846, or 1.28% of structured dollars, but accounted for 14.5% of its tokens. Supplying its records also added input cost to subsequent Sol repair requests. The deterministic logger incurred no model calls or invented token charge.

| Shift | None | Rolling | Structured |
| --- | --- | --- | --- |
| 1 | 8/8; 78 actions | 6/8; 65 actions; one interrupted, one unfinished | 8/8; 68 actions |
| 2 | 8/8; 81 actions | 7/8; 66 actions; one unfinished | 8/8; 68 actions |
| 3 | 8/8; 75 actions | 7/8; 66 actions; one unfinished | 8/8; 68 actions |

Per-ticket steps are shift 1 / 2 / 3. `I` is the retained spend interruption; `U` is an unfinished job-token outcome.

| Ticket | None | Rolling | Structured |
| --- | --- | --- | --- |
| Discovery | 9 / 9 / 9 | 9 / 9 / 9 | 9 / 9 / 9 |
| Healthy unit | 6 / 6 / 3 | 4 / 4 / 4 | 4 / 4 / 4 |
| Repeat plus cable | 10 / 10 / 10 | 8 / 8 / 8 | 8 / 8 / 8 |
| Physical cooling fault | 12 / 12 / 12 | 9 I / 10 / 10 | 10 / 10 / 10 |
| Transfer across chassis | 9 / 9 / 9 | 7 / 7 / 7 | 7 / 7 / 7 |
| Marked replacement | 9 / 9 / 9 | 9 / 9 / 9 | 9 / 9 / 9 |
| Factory return | 9 / 9 / 9 | 7 / 7 / 7 | 7 / 7 / 7 |
| Novel compound repair | 14 / 17 / 14 | 12 U / 12 U / 12 U | 14 / 14 / 14 |

Only passing independent tests count. All rolling compound attempts had completed physical work at action 12 but still needed power-on and certification. They stopped at **50,172 / 50,271 / 50,250 tokens**. Lower steps on those unfinished repairs are not a completed-service efficiency gain.

The job allowance is checked **between calls**. Structured received its passing test on action 14 at **52,973 / 52,363 / 54,673 tokens**; each writer was skipped afterward. These three successes and three rolling failures are the six job-allowance crossings, with a maximum overshoot of **4,673**. A strict pre-call 50k job cap would be a different experiment. Both whole-run ceilings were respected.

## What the traces show

**Scoped reuse and exceptions worked.** Rolling and structured took 18 sensor samples each; no memory took 46. Both memory policies avoided calibration remeasurement on applicable healthy/repeat/cooling/transfer/factory-return jobs, but still checked and repaired the repeat's independent cable fault. Both took two fresh samples for each marked replacement and each novel R3 compound sensor. The return to factory identity reused the factory calibration rather than its replacement-like installed settings.

Structured retained a scoped `raw = 2T + 10` fact after discovery, supplied it on later matching components, and acted consistently with reuse. Its final stores had 8 / 8 / 10 records, with maximum retained/supplied sizes of **1,321 / 1,282 / 1,418 tokens**. There were no rejected candidates or evictions. This establishes retention, supply and observable reuse on these fixtures; source validation alone does not establish every sentence's truth or a general causal benefit.

**Planning improved in some matched compound traces.** Sol structured gathered the independent evidence, repaired calibration/cooling/cable in one power-off period, restored power and tested in 14 actions in all shifts. Luna structured passed only shift 2: shift 1 discovered the cable after a failed test and ran out of allowance during recovery; shift 3 repeated an interlock probe and stopped before the final test. Sol no-memory used 14 / 17 / 14 actions versus Luna's 19 / 17 / 17. Its second shift still missed the cable until a failed test, so the larger model did not remove every inefficient path.

**Memory was not always the shortest path.** Sol without memory handled the third healthy unit with inspect, thermal probe and a passing independent test: three actions versus four for each memory policy. The certification tool itself checks all required properties. This is a valid shortcut in this synthetic world and a reminder to inspect what the benchmark rewards.

## Matched comparison against tuned Luna

The table includes success and unfinished terminal attempts, excluding the one globally interrupted position from both models. This yields **71 pairs: Luna 66 certified, Sol 68**. Do not silently turn the preserved interruption into a success or compare only successful trajectories.

| Memory | Paired positions | Certified, Luna → Sol | Actions, Luna → Sol | Total tokens, Luna → Sol | Estimated USD, Luna → Sol |
| --- | ---: | --- | --- | --- | --- |
| None | 24 | 24 → 24 | 248 → 234 | 524,517 → 470,232 | 0.0621629 → 1.048392 |
| Rolling | 23 | 20 → 20 | 200 → 188 | 723,174 → 649,779 | 0.0855138 → 1.408374 |
| Structured | 24 | 22 → 24 | 205 → 204 | 653,012 → 652,515 | 0.0806628 → 1.235156 |

Excluding rolling's four later positions with interrupted prior history leaves **19 rolling pairs**, with both models certifying 17; actions were 164 → 153 and tokens 573,382 → 510,180. None and structured retain their 24 unaffected pairs. The data also include the stricter 19 ticket/shift groups shared by every condition with uninterrupted history.

Structured's almost unchanged total actions and tokens conceal the outcome improvement: which actions reached the final test mattered. Yet its Sol cost was much higher. The configured repair model is the scientific factor changed; the separately authorized USD guard extension, interrupted history, stochastic writer outputs and independent model sampling are disclosed rather than treated as identical execution. Three repetitions of one fixed synthetic suite are exploratory evidence, not statistical proof or a general model ranking.

## Accounting, verification and sources

All **656 calls** returned complete known usage: **635 Sol repair calls** and **21 Luna writer calls**. Repair input/output was **1,671,988 / 40,549**, estimated **$3.749466**; writer input/output was **78,755 / 15,941**, estimated **$0.015846**. Zero API, writer or logger errors, unknown calls, incomplete responses, invalid tool actions or reservation violations. There was one failed certification test, followed by successful no-memory recovery. The only admission refusal was the original $0.50 stop; it was not retried.

Combined execution time was **1,186.93 seconds (19.78 minutes)**: 165.86 seconds in the original segment and 1,021.07 in the continuation. This excludes the authorization/testing pause. Attempt and execution times include local overhead and are not controlled model-latency measurements.

The post-run offline audit replayed **all 635 tool events**, regenerated the logs, verified certification/provenance/isolation/budgets, reconciled all role charges and reservations, and checked both frozen manifests. It also verified that all original calls and 11 attempt records were preserved exactly and that no started position received another call. The 120-test suite passed before continuation with dotenv and network disabled, including preservation, combined-spend admission and rejection of changed contracts or uncertain usage. No UI changes were made for this comparison; earlier desktop/mobile checks remain documented. Both previews remain stopped.

- [Combined configuration](../examples/evaluation-live-2026-10-29-sol-extended.json)
- [Manifest, segments, condition/shift aggregates and 72 positions](evaluation-results/2026-10-29-sol-extended/summary.json)
- [72-position role-token/cost/time CSV](evaluation-results/2026-10-29-sol-extended/attempts.csv)
- [Matched and sensitivity aggregates](evaluation-results/model-comparison-extended/comparison.json)
- [144-row Luna/Sol comparison CSV with inclusion/history flags](evaluation-results/model-comparison-extended/paired-attempts.csv)
- [World, eight tickets, tools and success requirements](EVALUATION_WORLD.md)

Publication files contain synthetic aggregates/configuration only. Raw transcripts, API IDs, credentials, local paths and database artifacts remain excluded. Prior reports and versions were preserved.

## Suggested follow-ups, not performed

1. **Test context cost separately.** Hold this world and prompts fixed while changing one common current-job representation or one declared memory supply budget. Rolling's failure occurred after correct physical work but before certification; adding a stronger model alone did not solve that resource constraint.
2. **Test planning as its own factor.** Compare one shared diagnose/work/verify instruction while keeping the model fixed. Inspect premature tests, repeated probes and unnecessary power cycles alongside success, rather than optimizing action count alone.
3. **Use held-out variants before client-level claims.** Preserve healthy controls, scope exceptions and independent certification. Do not infer that earlier weak-prompt behavior was caused solely by Luna, or that memory or a larger model is universally preferable.

No further paid evaluation or experimental tuning was performed after this terminal result. No merge, deployment or original-workshop restart was performed.
