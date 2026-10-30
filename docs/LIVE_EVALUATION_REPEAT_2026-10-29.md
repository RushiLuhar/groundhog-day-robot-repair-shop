# Exact repeat: A → A with tuned Luna

**All 18 repairs passed.** In every fresh pair, no memory took **9 → 9 tool actions**, while rolling and structured memory each took **9 → 7**. Both memory policies avoided the two sensor samples on the repeat while still inspecting the current machine, checking its physical condition, applying calibration and independently certifying the repair.

Memory saved actions on this exact repeat, but did not lower the complete pair's cost. Across three pairs, rolling used **4.2% more tokens and cost 5.2% more** than no memory; structured used **7.8% more tokens and cost 20.8% more**, including its writer. This small diagnostic separates successful reuse from the cost of carrying and maintaining that experience. It is not a general memory ranking.

## Frozen protocol

- Source: `4f57608683b37890d0c97fd6393a496d826a083d`, clean after **124 offline tests passed**. Run: `8940a814fbcb47f78c64d9be73795ad0`.
- New versioned fixture `service-repeat-v1 / standard-v1`: two copies of service-v2's first Amber calibration repair. Only the ticket number changes. Component/revision/origin, complaint, installed settings and all hidden physical state are identical. Each attempt creates a fresh world and needs a new passing test. No repeat hint or hidden answer is added to model input. [Task description](../repair_shop/tasks/README.md#exact-repeat-one-repair-twice) · [fixture](../repair_shop/evaluation/service_repeat.py).
- Three fresh pairs per condition, **18 attempts total**. Condition order rotates none/rolling/structured, rolling/structured/none, structured/none/rolling. Each condition sees A1 before A2; memory resets before the next pair.
- Repair and writer: **gpt-6-luna**, medium reasoning, **2,048 output tokens**, `repair-objective-v3` and `job-end-writer-v2`. Prompts, tools and public rules are identical to the preceding tuned Luna run. No policy is given the answer.
- Unchanged memory settings: **40 whole rolling entries, 3,000 retained tokens, 2,000 supplied tokens**. None discards cross-job history; both memory policies retain A1 within the pair. All conditions receive the same current-job context policy.
- **20 tool actions/job, 50,000 reported input + output tokens/job including writer; 2M tokens or $0.50 estimated for the run, whichever first.** Conservative admission before each call, no retries or model substitutions. Per-job allowance is checked between returned calls; no attempt approached it here.

Before launch, all nine historical tuned-Luna executions of this first ticket had complete nine-entry logs of 789–807 tokens, fitting the unchanged supply budget. Offline tests verified the same property. During the live run, a pre-repeat check required the complete actual rolling A1 log to equal both retained memory and A2 supplied context; it never failed. The fixture was not changed after observing results.

## Results

All conditions certified **6/6** attempts, with zero unfinished, interrupted, unattempted or infrastructure-error outcomes. No invalid actions, failed certification tests, rejected writer candidates or incomplete responses occurred.

| Memory | Actions | Sensor samples | Repair input | Repair output | Writer input | Writer output | Total tokens | Estimated USD | Attempt seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| None | 54 | 12 | 98,924 | 5,164 | 0 | 0 | 104,088 | 0.0124744 | 94.93 |
| Rolling | 48 | 6 | 102,778 | 5,684 | 0 | 0 | 108,462 | 0.0131198 | 96.59 |
| Structured | 48 | 6 | 88,954 | 5,341 | 13,688 | 4,267 | 112,250 | 0.0150682 | 138.73 |

Per-pair tokens below are input + output, split by role. All A1 and A2 repairs passed. Each A1 used two sensor samples; none A2 used two, while rolling/structured A2 used zero. Every row had zero invalid actions.

| Pair | Memory | Actions A1 → A2 | Repair tokens A1 → A2 | Writer tokens A1 → A2 |
| --- | --- | --- | --- | --- |
| 1 | None | 9 → 9 | 17,252 → 17,353 | 0 → 0 |
| 1 | Rolling | 9 → 7 | 17,555 → 18,522 | 0 → 0 |
| 1 | Structured | 9 → 7 | 17,588 → 13,925 | 2,922 → 3,323 |
| 2 | None | 9 → 9 | 17,344 → 17,292 | 0 → 0 |
| 2 | Rolling | 9 → 7 | 17,488 → 18,590 | 0 → 0 |
| 2 | Structured | 9 → 7 | 17,585 → 13,820 | 2,548 → 2,948 |
| 3 | None | 9 → 9 | 17,476 → 17,371 | 0 → 0 |
| 3 | Rolling | 9 → 7 | 17,635 → 18,672 | 0 → 0 |
| 3 | Structured | 9 → 7 | 17,596 → 13,781 | 2,596 → 3,618 |

Structured reduced repair-role tokens to **94,295**, but its six job-end writes added **17,955 tokens / $0.0035023**. This includes the writer after A2, as required by the unchanged policy, even though this short experiment has no subsequent repair to benefit from that write. Rolling's larger supplied context outweighed its two saved calls. Deterministic logs themselves made no model calls.

## Retained, supplied and used in observable behavior

Every pair began with empty memory. At rolling A2, **all nine A1 entries** were retained and supplied verbatim, occupying **807 tokens**, with no partial job. At structured A2, the one accepted semantic record from A1 was retained and supplied unchanged: **164 / 154 / 155 tokens** across pairs. Each record cited only that condition's A1 evidence, including measurements, calibration and the passing test. Nothing was evicted or rejected.

The structured fact was the scoped sensor relationship `raw = 2 × temperature + 10` for **TS-7 / R1 / factory**, distinct from the initially installed gain 1/bias 0. On A2, both memory policies inspected matching identity, checked airflow/temperature and continuity, applied gain 2/bias 10 without resampling, and passed the independent test. Ordering of physical checks and power-off varied slightly. This is behavior consistent with using the supplied evidence, with six saved actions per memory condition across three repeats. No memory repeated both sensor samples each time.

These are exact fresh-world repeats, unlike the earlier eight-ticket transfer sequence or repeated shifts whose memories reset. The older legacy-repeat observations are not pooled into this result: their world, prompts and controls differed. Three pairs of one synthetic repair cannot establish generalization, a model ranking, or the separate effect of any earlier prompt revision.

## Accounting and verification

Total: **324,800 tokens, $0.0406624 estimated, 330.37 seconds (5.51 minutes)**. All **156 calls** returned known usage: **150 repair calls and six writer calls**. Zero unknown usage, reservation violations or job/run-budget crossings; the largest attempt used **20,510 tokens**. No extra evaluation was run afterward.

The estimate uses the application's pinned standard rates, rechecked against the [official Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) on October 29: $0.10/M input and $0.50/M output. Cache discounts/write charges, taxes and regional/tier adjustments are excluded; this is not an invoice. Timings include local work and are not controlled latency measurements.

The offline post-run audit replayed every tool action in a fresh world, regenerated all 150 logs, verified certification, source ties, memory isolation and exact A1-to-A2 supply, reconciled all role usage/costs and checked reservations and the frozen manifest. The 124-test suite ran with dotenv and network disabled. An isolated credentials-disabled preview verified desktop (1440×900) and mobile (390×844) layout, the two-ticket count, saved configuration loading, a complete free run, replay, stop and reset. Production-callback tests also verified repeated runs and report export. The temporary preview was stopped; the original workshop and historical data were untouched.

- [Frozen configuration](../examples/evaluation-live-2026-10-29-repeat.json)
- [Manifest, condition/position aggregates, memory checks and all attempts](evaluation-results/2026-10-29-repeat/summary.json)
- [18-attempt role-token/cost/time CSV](evaluation-results/2026-10-29-repeat/attempts.csv)
- [Nine A1/A2 pairs with supply checks, role tokens, cost and time](evaluation-results/2026-10-29-repeat/paired-attempts.csv)

Publication files contain synthetic configuration and aggregate diagnostics only. Raw private traces, API IDs, credentials, local paths and databases remain excluded. No post-result prompt/task tuning, merge or deployment was performed.

The useful next question is how many genuine repetitions are needed to recover memory's lifecycle cost. That can be tested separately without adding a more elaborate world; it was not executed here.
