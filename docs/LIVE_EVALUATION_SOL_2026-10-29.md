# Sol repair-model comparison: bounded partial results

The corresponding-generation **gpt-6-sol** repair model completed ten certified repairs before the **$0.50 run admission guard** interrupted the next attempt. Recorded spend was **$0.4415131**, with **207,804 tokens** and no unknown usage. Of 72 planned positions, ten certified, one was interrupted and 61 were unattempted. This is a partial comparison, not a completed three-shift evaluation.

On the three early tickets completed by every condition, **Sol and tuned Luna had exactly the same tool counts and certifications**. Sol avoided one repeated interlock probe on an additional no-memory cooling repair. That single observation is insufficient to establish better tool use overall. The more demanding transfer, replacement, return-to-factory and compound tickets were not reached.

## Model choice and frozen protocol

The API model is `gpt-6-sol`, not the coding agent's model. The [official Sol model page](https://developers.openai.com/api/docs/models/gpt-6-sol), checked October 29, lists this identifier, medium reasoning and function calling. The authenticated model lookup also confirmed its availability before generation. It was selected to match the GPT-6 generation of the Luna baseline rather than changing generations. Standard text rates are **$2/M input and $10/M output**, twenty times [Luna's $0.10/M and $0.50/M](https://developers.openai.com/api/docs/models/gpt-6-luna). The independent writer remained `gpt-6-luna`.

Frozen clean source: **`e2e31c1be151cd5f14114ea4254dfc533e7f695d`**, after **110 offline tests passed** with credentials and network disabled. Only the experiment name and repair model differ from the [tuned Luna configuration](../examples/evaluation-live-2026-10-28-tuned.json). An offline equality check verifies this against the prior run's frozen manifest, including exact task description, public rules, tools and prompts.

Unchanged controls:

- `service-v2 / standard-v1`, `repair-objective-v3`, `job-end-writer-v2`; deterministic factual logs and the same public-only context.
- Eight ordered tickets × three conditions × three fresh shifts, maximum 72 attempts. Planned order rotates none/rolling/structured, rolling/structured/none, structured/none/rolling. Only the first shift's prefix executed.
- Medium repair and writer reasoning; matching **2,048 output caps**; 20 tool actions/job; 40 rolling entries, 3,000 retained and 2,000 supplied memory tokens.
- **50,000 reported input + output tokens/job including the writer**, **2M run tokens OR $0.50 estimated**, whichever first. Conservative admission, no retries, substitution, top-up or resumption.

The per-job allowance remains checked between returned calls. No Sol attempt reached it or overshot it. Estimates use pinned standard rates, excluding cache, regional/tier adjustments and taxes; they are not invoices.

Reproduction and chart sources:

- [Exact Sol configuration](../examples/evaluation-live-2026-10-29-sol.json)
- [Manifest, aggregates and all 72 scheduled positions](evaluation-results/2026-10-29-sol/summary.json)
- [Sol attempt CSV](evaluation-results/2026-10-29-sol/attempts.csv)
- [Matched Luna/Sol aggregates](evaluation-results/model-comparison/comparison.json) and [144-row comparison CSV with explicit inclusion flags](evaluation-results/model-comparison/paired-attempts.csv)
- [Factual world, task and tool explainer](EVALUATION_WORLD.md)

These files contain synthetic aggregates and frozen configuration, not raw transcripts, API identifiers, secrets, databases or private paths. Historical configuration files are not authorization for new paid runs.

## Coverage and accounting

All steps and tokens below include the interrupted attempt. Each condition had 24 scheduled positions; denominators are not silently reduced to completed work.

| Memory | Certified / scheduled | Job-cap unfinished | Interrupted | Unattempted | Steps | Repair tokens | Writer tokens | Total tokens | Estimated USD | Attempt seconds |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| None | 4/24 | 0 | 0 | 20 | 37 | 72,358 | 0 | 72,358 | 0.1625800 | 67.09 |
| Rolling | 3/24 | 0 | 1 | 20 | 30 | 85,562 | 0 | 85,562 | 0.1850200 | 47.37 |
| Structured | 3/24 | 0 | 0 | 21 | 21 | 41,257 | 8,627 | 49,884 | 0.0939131 | 51.34 |

The run took **165.86 seconds**. All **91 requests** returned complete, known usage: 88 repair calls, three writer calls. Repair reported **193,965 input + 5,212 output**, estimated **$0.4400500**; writer reported **7,126 input + 1,501 output**, estimated **$0.0014631**. There were zero API, writer or logger errors, incomplete responses, invalid tool actions, failed tests, unknown calls or reservation violations.

The guard refused the next rolling ticket-4 request before sending it. Its conservative reservation was 23,647 input + 2,048 output tokens, estimated $0.067774; adding that to recorded spend would reach **$0.5092871**. Actual usage for that unsent request is not known or invented. The conservative guard intentionally leaves unused headroom.

Rolling had vented, aligned, sealed and powered the unit back on after nine actions. **Certification was still absent**, so it remains interrupted even though the physical state was ready for a test. The interruption is a run-spend outcome, not an API error, output truncation, job-token failure or evidence that Sol could not solve the ticket.

## Matched evidence against tuned Luna

The strict common subset is **shift 1, tickets 1–3**, three attempts per condition in each run. Both models certified all nine of these positions.

| Memory | Steps, Luna → Sol | Sensor samples, Luna → Sol | Repair tokens, Luna → Sol | Writer tokens, Luna → Sol | Estimated USD, Luna → Sol |
| --- | --- | --- | --- | --- | --- |
| None | 25 → 25 | 6 → 6 | 47,594 → 46,636 | 0 → 0 | 0.0056718 → 0.1037440 |
| Rolling | 21 → 21 | 2 → 2 | 52,066 → 50,855 | 0 → 0 | 0.0061642 → 0.1116300 |
| Structured | 21 → 21 | 2 → 2 | 42,213 → 41,257 | 9,427 → 8,627 | 0.0069476 → 0.0939131 |

Per-ticket steps were identical: discovery **9/9/9**, healthy **6/4/4**, and calibration repeat plus cable **10/8/8** for none/rolling/structured. Both memory policies avoided repeated low/high samples on the healthy and repeat tickets. They still probed the current unit, detected the repeat's cable fault, performed both required repairs in one power-off period and obtained independent certification. No-memory sampling is expected given its lack of cross-job evidence; it should not be mislabeled as failure to use supplied memory.

Structured retained a 167-token semantic record after discovery: the observed `raw = 2T + 10` relationship, scoped to TS-7/R1/factory, with sample/write/test sources. It supplied that record on the healthy job and a 307-token store on the next repeat. The store then reached 489 tokens, with one semantic and two episodic records; no rejection or eviction occurred. Retention, supply and the absence of new calibration samples are consistent with reuse. The writer is stochastic even though its model/settings are fixed, so its differing token counts are not a repair-model-only direct effect.

There is one additional terminal same-condition pair: **no-memory ticket 4**, Luna 13 actions versus Sol 12, both passing. Luna probed interlocks again after venting; Sol used one interlock probe and followed the observed vent-before-align ordering. Their total tokens were 29,087 versus 25,722. This is one trace-level improvement, not repeated evidence of a general model advantage. Rolling ticket 4 is excluded from completed-service efficiency comparisons; structured ticket 4 and all later tickets were unattempted.

The comparison changes only the configured repair model, but independent sampling, model-specific token accounting and downstream writer content still vary. The equal dollar ceiling caused unequal coverage. No second/third Sol shift ran, so there is no Sol across-shift variation estimate. Do not compare Sol's 4/24, 3/24 and 3/24 planned-position coverage directly with Luna's complete 24-position condition totals as a capability ranking.

## Verification and next decisions

The offline result audit replayed **all 88 tool events** against the frozen world, regenerated the literal logs and checked passing-test certification, exact provenance, memory isolation and budgets, all call/attempt/role totals, per-role prices, reservations and the manifest/source fingerprint. The current 110-test suite covers mixed Sol-repair/Luna-writer accounting and pre-send USD refusal. Earlier desktop/mobile production-callback checks remain applicable; this change adds pricing/configuration, results and documentation, with no UI changes. Both localhost previews remain stopped.

1. **Keep the conclusion narrow.** The early memory-use behavior matches tuned Luna. Do not attribute the older weak-prompt run's behavior solely to a Luna-class model, or claim Sol resolves compound planning from this prefix.
2. **Complete coverage only under a separately frozen authorized protocol.** The $0.50 run is terminal and preserved. More budget would be needed to observe later exceptions and repeated shifts; a new run or any explicitly supported continuation needs a recorded protocol, not a silent edit to this result.
3. **Retain the current tasks/prompts for a model comparison.** There is no evidence here warranting further tuning to improve Sol's score. Context representation, completion planning and held-out variants remain separate proposed experiments from the Luna report.

No additional paid run, task/prompt tuning, merge or deployment followed this terminal result as part of this report.
