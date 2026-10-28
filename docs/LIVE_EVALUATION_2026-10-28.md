# Luna memory evaluation — 2026-10-28

The live evaluation found occasional action savings from memory, but no structured-memory advantage on this fixed suite. Larger request contexts exhausted the per-job allowance before several repairs could be certified. Structured notes preserved useful calibration evidence, yet the repair model usually measured again. These are observations about this model, prompts, suite and budgets, not a general ranking of memory architectures.

## Frozen protocol and actual exposure

The owner authorized up to three fresh shifts of eight tickets across three memory conditions, with a 1,000,000-reported-token / $1-estimated-cost ceiling. Execution used clean source commit `6c8abedc26e4f18df42cff55b0c824ddb84a521f`. The [exact configuration](../examples/evaluation-live-2026-10-28.json) and [sanitized manifest and aggregates](evaluation-results/2026-10-28/summary.json) preserve prompts, tools, task fingerprint, source, versions, pricing and condition order. [Per-attempt CSV](evaluation-results/2026-10-28/attempts.csv) includes all 72 scheduled rows, role usage, outcomes, steps and elapsed time.

| Control | Frozen value |
| --- | --- |
| Task / variant | `service-v1` / `standard-v1`; same ordered eight tickets |
| Repair role, all conditions | `gpt-6-luna`, medium reasoning, `repair-objective-v1`, 2,048 output tokens |
| Structured writer | Independent `gpt-6-luna`, medium, `job-end-writer-v1`, 2,048 output tokens; one job-end call when allowance remains |
| Memory | None; rolling whole factual entries; typed structured factual-log records |
| Memory limits | 40 rolling entries; 3,000 retained tokens; 2,000 supplied tokens |
| Per job | 20 tool actions; 30,000 returned input + output tokens including writer |
| Run | Conservative request admission; 1,000,000 tokens or $1 estimated spend |
| Order | Shift 1: none, rolling, structured; shift 2: rolling, structured, none; shift 3 planned: structured, none, rolling |

Memory started empty for every condition and repetition. Current-job context and repair objective were common to all conditions. Deterministic logs rendered actual tool results; they made no API calls or calibration inferences. No scripted repair/writer policy was used. Configuration persistence was round-tripped before calls. No model substitution, retries, mid-run tuning or replenishment occurred.

The run **stopped cleanly after 46 started attempts**: 39 certified, six unfinished at the job allowance, one interrupted by the run admission guard, and 26 unattempted. Shift 1 completed; shift 2 completed tickets 1–7 for every condition and four actions on rolling ticket 8. Shift 3 never started. The remaining 16,780 tokens could not admit the next request's conservative 20,748-token reservation. No reservation was exceeded by returned usage.

There were **409 returned calls, zero unknown calls, zero API/infrastructure errors, zero logger/writer errors and zero incomplete responses**. All returned model identifiers were `gpt-6-luna`, with service tier `default`. Total execution time was **865.64 seconds (14.43 minutes)**, including local persistence overhead.

## Outcomes before efficiency

For an equal-exposure comparison, include shift 1 tickets 1–8 and shift 2 tickets 1–7: **15 paired ticket groups, 45 attempts**. Keep job-budget failures in these denominators. Exclude the globally interrupted rolling attempt and its unattempted peers. Do not rank the unequal full-run condition totals.

| Condition | Certified / matched attempts | Unfinished | Tool actions | Total tokens | Writer tokens included | Estimated USD | Attempt time (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| No cross-job memory | 14/15 | 1 | 141 | 227,353 | 0 | 0.0290501 | 288.97 |
| Rolling logs | 13/15 | 2 | 121 | 367,678 | 0 | 0.0419442 | 236.76 |
| Structured records | 12/15 | 3 | 133 | 375,554 | 40,504 | 0.0453910 | 332.90 |

Fewer actions here do not necessarily mean greater efficiency: an attempt that stops before its final test also takes fewer actions. Under the same job allowance, context size is part of the measured intervention. It is also a constraint that prevents this run from answering how well each policy would repair with sufficient allowance.

| Exposure | No memory: passes, steps, tokens | Rolling: passes, steps, tokens | Structured: passes, steps, tokens |
| --- | --- | --- | --- |
| Shift 1, all eight tickets | 7/8; 81; 135,801 | 6/8; 65; 199,627 | 6/8; 70; 204,829 |
| Shift 2, matched tickets 1–7 | 7/7; 60; 91,552 | 7/7; 56; 168,051 | 6/7; 63; 170,725 |

First-shift detail follows. Each cell is **steps / total tokens**, including any writer. `U` means unfinished at the job-token allowance; every other cell is certified.

| Ticket | No memory | Rolling | Structured |
| --- | ---: | ---: | ---: |
| 1 — discover calibration | 9 / 13,720 | 9 / 13,782 | 10 / 18,788 |
| 2 — healthy control | 6 / 7,764 | 4 / 7,963 | 4 / 9,090 |
| 3 — different initial settings | 11 / 18,947 | 7 / 18,022 | 9 / 23,450 |
| 4 — cooling fault | 12 / 21,309 | 9 / 30,557 U | 11 / 31,732 U |
| 5 — component transfer | 9 / 13,764 | 9 / 32,445 | 9 / 30,187 |
| 6 — marked replacement | 9 / 13,651 | 9 / 32,203 | 9 / 30,321 |
| 7 — factory return | 9 / 13,729 | 9 / 32,302 | 9 / 30,315 |
| 8 — novel compound repair | 16 / 32,917 U | 9 / 32,353 U | 9 / 30,946 U |

The job allowance uses returned usage, so one request can cross 30,000 tokens. If that request produces a passing test, the pass remains valid; otherwise another request is refused. For example, rolling ticket 4 passed on its tenth action at 34,055 tokens in shift 2, whereas shift 1 stopped after nine actions without a test. The global conservative admission guard is separate and remained below its ceiling.

## What the traces establish

- **Early repeat:** rolling ticket 3 used no sensor samples and calibrated from earlier evidence in both shifts, passing in seven actions. No memory used two samples and took 11 then nine actions. This behavior is consistent with useful reuse, though extra probes and an unnecessary rejected vent account for part of the first-shift difference. Structured memory supplied source-linked gain 2 / bias 10 evidence but still sampled twice, taking nine actions in both shifts. Supplying evidence did not establish that it changed the decision.
- **Healthy control and variation:** rolling passed in four actions in both shifts without repair or sampling. Structured did so in shift 1, but sampled again and took six actions in shift 2. No memory took six then five. A single trajectory would have hidden this variation.
- **Transfer:** all conditions measured twice and took nine actions on ticket 5 in both shifts. Structured factory evidence was retained and supplied, but no action savings appeared on the new chassis. Its notes repeatedly restricted claims to observed units/configurations.
- **Replacement and return:** all conditions measured the replacement's different calibration and later used the original factory calibration correctly, taking nine actions on each ticket. In shift 1, structured maintenance was skipped after the replacement because its job allowance was exhausted. In shift 2, a separate replacement-origin record was retained and supplied alongside factory records for ticket 7. The agent still remeasured, so these outcomes show correct repairs, not proof that memory caused correct exception handling.
- **Cooling and compound faults:** the unfinished cooling attempts completed the physical sequence but never called the independent test. All first-shift compound attempts were unfinished. No memory reached a test, failed because the cable still needed service, then reseated it but exhausted its allowance before powering on and retesting. The memory conditions stopped earlier. Correctly displaying a calibrated temperature never certified away a real physical fault.
- **Writer behavior:** ten writer calls accepted 13 records with zero rejected candidates or budget evictions. Notes were episodic/procedural; none were semantic. Exact-text deduplication retained rewritten near-duplicate procedures. The first shift grew to seven records and 1,684 supplied tokens; the second reached six retained records after ticket 7. Five of the 15 started structured jobs skipped maintenance because of the job allowance. The writer receives observations and previous records but not the public world instructions supplied to repair; this is a plausible contributor to narrowly scoped notes, not an established cause.

These findings came from manual inspection of the repeat, transfer, replacement, factory-return and compound traces, including source ties and supplied records. There is no automated semantic grader or counterfactual causal-use test. Raw transcripts, API identifiers, databases and local paths are excluded from the publication artifacts.

## Usage and cost

| Role | Calls | Input tokens | Output tokens | Estimated USD |
| --- | ---: | ---: | ---: | ---: |
| Repair | 399 | 900,632 | 42,084 | 0.1111052 |
| Memory writer | 10 | 33,998 | 6,506 | 0.0066528 |
| Total | 409 | 934,630 | 48,590 | **0.1177580** |

Total reported usage was **983,220 tokens**. Writer maintenance was 40,504 tokens: 10.8% of structured usage, in addition to the cost of supplying stored notes on repair requests. Deterministic logging has no model-call charge; its rendered text contributes to later input usage. The interrupted rolling attempt adds four actions and 12,635 tokens to the matched table's totals, giving 399 actions overall.

The estimate applies the pinned [official Luna standard rates](https://developers.openai.com/api/docs/models/gpt-6-luna), checked October 28: $0.10/M input and $0.50/M output. [Default service tier](https://developers.openai.com/api/reference/cli/resources/responses/methods/create) was explicitly requested. The largest returned input was 5,948 tokens, below the long-context pricing threshold; the largest output was 1,148, below the 2,048 cap. Estimates omit cache discounts, cache-write premiums, region adjustments and taxes; they are not an invoice. Known usage is complete for every sent request.

## Suggested next changes, in order

1. **Separate repair feasibility from cost pressure.** Keep this constrained result. For a separately authorized next pilot, predeclare a higher common job allowance while keeping the task, model, prompts, memory and step cap fixed. Size a complete 24-attempt run from these measured contexts, with conservative headroom and an independent global safety ceiling. Do not just add harder tickets: even the current compound case lacks a completed live outcome under this allowance.
2. **Test a concise, scoped writer contract.** On frozen observation fixtures first, supply the writer the same public component/origin invariants available to repair and ask it to distinguish reusable relationships from case-specific procedures. Require exact evidence and exception scope. Separately evaluate stable claim identifiers and supersession for near-duplicate notes; exact-text deduplication cannot merge paraphrases. Neither intervention should preload the correct calibration or guarantee a structured-memory win.
3. **Evaluate repair decisions and context overhead.** The trace shows unnecessary probes, one vent on already-clear airflow, repeated measurement despite evidence, and certification delayed until the allowance ran out. Test one versioned common prompt/context change at a time, applied across policies. Preserve raw events in the audit even if a future request format avoids sending both raw results and literal renderings of the same current-job evidence. Continue to require the final test.
4. **Then vary reasoning/model/budget independently.** Hold writer settings fixed for repair-model or reasoning comparisons and use exactly the requested conditions. Add fixture variants and complete fresh repetitions only after feasibility is understood. The current pilot measures memory-policy behavior at one repair model/effort, not the effect of changing those settings.

These are proposals, not changes made after seeing scores. No experimental prompt, task, memory or model change was implemented during or after this evaluation.

## Verification and limits

The offline acceptance baseline was **96 passing tests**; three admission/compatibility tests raised it to **99 before live execution**. Network and dotenv loading were disabled in test processes. Prior production-callback browser checks covered desktop 1280×900 and mobile 390×844, two/three conditions, fresh repetitions, config versions, trace/replay/export, stop/reset, API/writer failures and budget/truncation outcomes. See [the acceptance record](EVALUATION_HARNESS_V2.md#final-offline-acceptance-2026-10-28). Those checks used injected free policies and are distinct from this live run. The temporary preview is stopped; the original workshop and legacy data were preserved.

Post-run checks reproduced all 399 literal log entries from their raw events, verified certification against passing tests, checked memory source/condition/repetition boundaries and supplied budgets, reconciled every role/attempt total, validated the frozen manifest hash and configuration, and checked all 72 published rows. The publication scan found no secrets, private paths, API identifiers or raw transcripts in the changed files.

Only one whole shift and one seven-ticket paired prefix completed. This deterministic world has one variant, ordering is fixed within each condition, and the provider returned an alias rather than a dated model snapshot. Repetition variance, task breadth and causal attribution remain unresolved. Frozen manifests make the setup inspectable; they do not promise identical future model responses. The reproducible outcome is a bounded, partially completed evaluation with honest denominators, not statistical proof that a memory design is superior.
