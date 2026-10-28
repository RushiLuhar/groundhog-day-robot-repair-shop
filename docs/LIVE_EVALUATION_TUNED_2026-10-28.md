# Memory-first prompt and task intervention: live evaluation

The tuned run completed all **72 attempts: 67 certified, five unfinished**, with zero interrupted or unattempted jobs. Structured memory now produced compact scoped facts and consistently avoided repeated calibration measurements on applicable tickets. It still failed two compound repairs under the job allowance. No cross-job memory certified all 24 repairs and cost less overall.

This is a **combined intervention**: repair prompt, writer prompt/public context and task version changed together. It is not a causal estimate of the memory-use instruction alone. Three repetitions of one fixed synthetic sequence do not establish a general ranking.

## Frozen protocol

Source: `f20daf098f365bfc99f7db2973e7a0a46a32108b`, clean when execution began. **107 offline tests passed before paid execution**, with dotenv loading and network disabled. There were no code/config changes or retries during the run.

- `service-v2` / `standard-v1`: eight ordered tickets, three fresh shifts, three memory conditions. Condition order rotated none/rolling/structured, rolling/structured/none, structured/none/rolling. Memory reset between shifts.
- The same `repair-objective-v3` instruction for every condition: inspect supplied memory before diagnosis; establish component/revision/origin applicability; reuse supported facts when observations do not contradict them; verify exceptions and independently certify the current unit.
- Independent `job-end-writer-v2`, with public transfer rules and concise scoped records; deterministic literal logs unchanged. No extra reflection, retrieval or grading model.
- `gpt-6-luna`, medium reasoning and **2,048 output tokens** for repair and writer; 20 tool actions/job; 40 rolling entries, 3,000 retained tokens, 2,000 supplied tokens.
- **50,000 combined repair/writer input + output tokens/job**, **2,000,000 run tokens**, **$0.50 estimated run spend**. Conservative run admission; no retries, substitutions or top-ups.

The versioned task changes add a cable fault to the early calibration repeat, start the returning factory unit with replacement-like settings, and make the revised compound unit display a normal-looking temperature despite genuine heat. Public rules/test feedback clarify operation constraints and power preconditions. [The tuning record](EVALUATION_TUNING_V2.md) explains the evidence and preserves the prior versions.

Reproduction and chart inputs:

- [Exact live configuration](../examples/evaluation-live-2026-10-28-tuned.json)
- [Frozen manifest, per-condition/per-shift aggregates and 72 safe attempt records](evaluation-results/2026-10-28-tuned/summary.json)
- [72-attempt CSV with role input/output, cost and elapsed time](evaluation-results/2026-10-28-tuned/attempts.csv)
- [Before/after intervention aggregates](evaluation-results/tuning-comparison/comparison.json) and [144-row comparison CSV](evaluation-results/tuning-comparison/paired-attempts.csv)

The cross-version data align sequence positions, not identical task definitions: tickets 3, 7 and 8 have different fixtures, and public rules/prompts changed across the suite. Raw transcripts, API identifiers, credentials, private paths and databases are excluded. Historical live configurations do not authorize further paid runs.

## Results, including unfinished attempts

| Memory | Certified | Unfinished | Steps | Repair tokens | Writer tokens | Total tokens | Estimated USD | Attempt seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| None | 24/24 | 0 | 248 | 524,517 | 0 | 524,517 | 0.0621629 | 454.97 |
| Rolling | 21/24 | 3 | 211 | 768,076 | 0 | 768,076 | 0.0905212 | 518.01 |
| Structured | 22/24 | 2 | 205 | 559,366 | 93,646 | 653,012 | 0.0806628 | 589.13 |

All five unfinished attempts were compound jobs stopped by the per-job allowance. Lower steps on an unfinished repair are not a completed-service efficiency gain. Structured used fewer tokens and dollars than rolling in this run, but more than no memory while certifying fewer repairs. Its writer accounted for 93,646 tokens, **14.3%** of its total, and $0.0156322; supplying notes adds input cost to repair requests as well.

| Shift | None | Rolling | Structured |
| --- | --- | --- | --- |
| 1 | 8/8; 84 steps | 7/8; 68 steps | 7/8; 69 steps |
| 2 | 8/8; 81 steps | 7/8; 73 steps | 8/8; 68 steps |
| 3 | 8/8; 83 steps | 7/8; 70 steps | 7/8; 68 steps |

Step counts are shift 1 / 2 / 3; `U` marks unfinished.

| Ticket | None | Rolling | Structured |
| --- | --- | --- | --- |
| 1 — discovery | 9 / 9 / 9 | 9 / 9 / 9 | 9 / 9 / 9 |
| 2 — healthy | 6 / 6 / 6 | 4 / 4 / 4 | 4 / 4 / 4 |
| 3 — calibration repeat plus cable | 10 / 11 / 10 | 8 / 10 / 10 | 8 / 8 / 8 |
| 4 — cooling | 13 / 11 / 14 | 11 / 12 / 10 | 10 / 10 / 10 |
| 5 — transfer across chassis | 9 / 9 / 9 | 8 / 9 / 9 | 7 / 7 / 7 |
| 6 — marked replacement | 9 / 9 / 9 | 9 / 9 / 9 | 9 / 9 / 9 |
| 7 — factory return | 9 / 9 / 9 | 7 / 8 / 7 | 7 / 7 / 7 |
| 8 — compound with misleading indication | 19 / 17 / 17 | 12 U / 12 U / 12 U | 15 U / 14 / 14 U |

## What the traces support

**Retention, supply and behavior now line up on the repeats.** The first structured note recorded the TS-7 R1 factory relationship `raw = 2 × temperature + 10`, distinguished it from the initial installed settings, cited observations and a passing test, and stated its component/revision/origin applicability. Applicable evidence was supplied on later jobs. Structured made zero sensor samples on tickets 2, 3, 4, 5 and 7 in every shift; it sampled twice on discovery, replacement and the novel revision. That is 18 samples total, versus 48 without memory and 23 with rolling logs.

On the repeated component, structured still probed continuity and repaired the added cable fault before certification: eight actions in all three shifts, versus ten or eleven without memory. On chassis transfer and factory return it used seven actions versus nine without memory. These actions are consistent with useful reuse; supplied evidence alone would not establish that. The live comparison is small and stochastic, and the cross-version changes do not isolate a single cause.

**Exceptions remained active.** All three conditions took two samples on each marked replacement and installed its different calibration. Structured then returned to the factory calibration without new samples on ticket 7, even though that unit started with the replacement's settings. No condition blindly reused the old calibration on the novel R3 compound component; all sampled it twice. Both memory policies handled the repeat's independent cable fault.

**The new writer produced shorter stores, not zero maintenance cost.** The three shifts accepted 6 / 7 / 8 records, with final stores containing 3 / 2 / 3 semantic records plus procedural/episodic notes. There were no rejected candidates or evictions. Maximum retained/supplied structured context was 1,035 / 1,214 / 1,289 tokens, below the 2,000-token supply ceiling. Returned records used at most 54 words and at most two additions per writer call. The preceding v1 run produced no semantic records and approached the retention/supply ceilings. This is observed contract compliance, not a new schema-enforced word limit or a guarantee that every claim is true. Citation validity is not semantic validation.

**The compound outcome depended on completion, planning and context cost.** All rolling compound attempts stopped after 12 actions at 51,998 / 52,181 / 52,130 tokens. In shifts one and three, physical work was complete but power-on and certification remained; in shift two, the cable fault had been diagnosed but not repaired. Structured shift one fixed the cable after a failed test, then stopped at 15 actions/54,102 tokens before power-on and retest. Shift three repeated an interlock probe, completed physical work and powered on, but stopped at 14 actions/53,335 tokens before certification. Shift two batched the work into one power-off period and passed at action 14/52,078 tokens; its writer was skipped afterward. No-memory paths needed 17–19 actions, including recovery after a failed test, but their shorter contexts allowed all three to certify.

## Compare with the preceding 50k run

Both runs attempted all 24 sequence positions per condition. Controls other than name, prompt versions and task identity were unchanged. The task changes mean these are descriptive before/after results, not equal-task treatment effects.

| Memory | Certified, v1 → tuned | Steps, v1 → tuned | Tokens, v1 → tuned | Estimated USD, v1 → tuned |
| --- | --- | --- | --- | --- |
| None | 23/24 → 24/24 | 253 → 248 | 448,267 → 524,517 | 0.0588871 → 0.0621629 |
| Rolling | 21/24 → 21/24 | 215 → 211 | 692,168 → 768,076 | 0.0797424 → 0.0905212 |
| Structured | 21/24 → 22/24 | 232 → 205 | 782,197 → 653,012 | 0.0954169 → 0.0806628 |

Structured remeasurement fell from 48 to 18 samples and its stores stayed smaller. None/rolling total tokens increased despite fewer actions; request content and trajectories also changed. Total run spend was similar ($0.2340464 → $0.2333469), with 65 → 67 certifications. This is useful evidence about the implemented prototype, not proof that structured memory is universally better or that the stronger instruction alone caused the differences.

## Accounting and verification

Execution took **1,563.17 seconds (26.05 minutes)**. **685 calls** returned known usage: 664 repair calls and 21 writers. Repair reported 1,770,662 input + 81,297 output tokens; writers reported 77,977 input + 15,669 output. Total **1,945,605 tokens**, **$0.2333469 estimated**. Zero API, writer or logger errors; zero unknown usage, incomplete responses, reservation violations or admission refusals. All returned models were Luna, tier `default`; the largest returned input was 5,611 tokens and output 1,457.

Per-job allowance is checked **between calls**, after returned usage, including writer tokens. Eight attempts crossed 50,000 on a returned call: five unfinished compound attempts, plus no-memory shift-one compound (51,164), rolling shift-two cooling (51,720) and structured shift-two compound (52,078), each of which received its passing test on that call. The largest overshoot was 4,102 tokens. A returned passing test counts as certification; reaching the allowance without one does not. Both whole-run ceilings were respected.

Pricing uses the [pinned official Luna standard rates](https://developers.openai.com/api/docs/models/gpt-6-luna), checked October 28: $0.10/M input and $0.50/M output, below the long-context threshold. Estimated USD excludes cache adjustments, regional adjustments and taxes and is not an invoice. Attempt/total elapsed times include local overhead and are not model-only latency measurements.

Post-run offline audit replayed all **664 raw tool events** against the frozen world and regenerated every literal observation. It checked certification against passing tests, exact source ties, fresh memories, whole-entry/record budgets, call/attempt/role totals, pricing, reservations, exact configuration and the clean source/manifest fingerprint. The new offline preset also completed 24/24 free demo attempts in the isolated UI; desktop/mobile layout and the earlier two/three-condition, version/replay/stop/reset/export/error checks passed. The temporary preview is stopped; the original workshop and legacy data were untouched.

## Prioritized follow-ups, not performed

1. **Isolate the intervention.** Hold one task version and repair prompt fixed while changing only the writer contract; separately compare the repair memory-use instruction. This run cannot separate those effects.
2. **Examine context and completion planning.** The common current-job request includes raw results and literal logs, while memories add more input. Test one common representation or a better shared work/verification plan as a separate versioned factor, with exactly the same certification requirements. Do not remove the final test to make capped repairs appear successful.
3. **Add held-out variants before broad claims.** Vary component relationships and fault combinations while preserving public solvability, then compare model/reasoning settings with the writer fixed. Preserve negative controls and report failures and maintenance cost alongside saved actions.

No additional paid run or post-result implementation change was made after this evaluation. The repository contains the measured frozen versions and analysis for review, not an automatically tuned winner.
