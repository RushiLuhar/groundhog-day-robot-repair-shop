# Post-evaluation prototype: scoped facts and diagnostic counterexamples

These changes were made **after** the [50k live evaluation](LIVE_EVALUATION_50K_2026-10-28.md). They have **no live performance result**. The measured run used `service-v1`, `repair-objective-v1` and `job-end-writer-v1`; its configuration and results remain frozen. The old defaults, prompt texts, task fixtures and request behavior remain available without migration.

Load the **tuned-v2** preset or [offline example](../examples/evaluation-tuned-v2.json) in the separate evaluation UI. It explicitly selects `service-v2`, both v2 prompts, Luna/medium, 2,048 output caps and the 50k job / 2M run-token / $0.50 controls. It has `live: false`; it authorizes no paid run. The UI now displays task/variant identity alongside condition counts.

## Evidence → versioned change

| Observed issue in the unchanged live protocol | Prototype change | What remains uncertain |
| --- | --- | --- |
| Structured memory retained correct calibration yet remeasured every ticket; narratives repeatedly limited support to one case | `job-end-writer-v2` receives the same public task rules as repair and asks for concise semantic relationships with component/revision/origin applicability | Whether a live writer produces useful abstractions, and whether repair uses them |
| Rewritten procedures and overlapping citations grew to retention/supply limits | Ask for at most three additions, about 60 words per record, minimal sufficient citations and omission of unchanged facts | These are prompt requests, not new schema-enforced limits; paraphrases can still accumulate |
| Agents mistook interlocks for faults and attempted unnecessary work on clear airflow | `repair-objective-v2` distinguishes constraints from repair need and focuses measurements on unresolved uncertainty | Whether the extra instructions reduce unnecessary actions or add distracting context |
| A no-memory attempt tested with power off, then wandered until output truncation | Track latest state in the common prompt; `service-v2` returns explicit power-on test-precondition feedback | This makes an observable precondition clearer; it does not explain failed physical certification |
| Compound failures overlooked an independent cable fault or ran out before certification | Common prompt separates remembered calibration from current physical faults; new task counterexamples exercise this distinction earlier | Whether behavior transfers to different tasks/models; no guaranteed memory advantage |

The writer still sees observations, existing records and source identity/pass metadata, never hidden fixtures or a raw-history backup. It can infer relationships from evidence under public rules; the deterministic logger still performs no diagnosis or arithmetic inference. Existing validation, exact-text deduplication, retention/supply budgets and audits are unchanged. No stable claim-key infrastructure, semantic deduplicator, reflection agent, learned retrieval or extra model call was added.

## New task identity: service-v2 / standard-v1

The eight-ticket sequence and trusted task interface remain small. Public complaints stay the same; author-facing fault labels below are not sent to agents.

| Ticket | Change from service-v1 | Decision tested |
| --- | --- | --- |
| 1, 2, 4, 5, 6 | Fixtures unchanged | Preserve discovery, healthy control, genuine cooling, chassis transfer and marked replacement |
| 3 | Same sensor calibration repeat, plus a loose cable | Reusing calibration does not imply replaying the entire previous repair |
| 7 | Factory unit starts with the replacement's gain 3 / bias -5 | Current component identity and installed settings are distinct; the most recent exception must not overwrite factory evidence |
| 8 | Revised sensor gain 2 / bias -12, installed gain 4 / bias -12 | Indication looks like 40 while true temperature is 80; calibration cannot hide genuine heat, and cable/order requirements remain |

Only `ServiceWorldV2` adds the explicit power-off test response. Its remaining mechanics and independent certification are inherited from the preserved world. Task identity, implementation version and fixture fingerprint distinguish the new semantics. A cold repair remains possible through public observations; wrong ordering, unresolved cable faults, real heat and wrong calibration still prevent certification.

## Offline acceptance and interpretation

**105 tests passed** with network connections and dotenv loading disabled, up from the preceding 99-test baseline. New regressions verify frozen v1 prompts/task fingerprints and configuration round trips; all v2 cold/memory-assisted paths; the normal-looking overheating case; ordering and independent certification; public-only writer rules and role controls; and production callbacks with exactly two or three conditions, saved versions, fresh repetitions, replay and exports. Two benign pytest assertion-rewrite warnings concerned already-imported dependencies.

The scripted repair/writer policies do not execute model prompts. Their successes verify world solvability, accounting and UI mechanics—not semantic quality or improved model performance. An isolated localhost preview with temporary storage and paid clients disabled passed desktop (1280 × 900) and mobile (390 × 844) checks: three conditions / 24 certified demo attempts; two conditions / 16; two fresh repetitions / eight; configuration versions 1 and 2 with old-version reload; trace inspection, saved-run loading, replay, report export, stop and reset. A two-attempt tool-step-cap run showed both attempts unfinished, and an unsupported writer prompt was rejected. Mobile had no page-level horizontal overflow; wide result tables scroll within their container. The temporary preview was stopped afterward; the original workshop and its database were untouched.

The combined prototype changes repair prompt, writer contract and task version. A later causal comparison should isolate them: for example, first hold `service-v1` and repair-v1 fixed while changing only the writer contract. Then test a common repair-prompt change with the writer fixed. Any new live run requires its own approved scope; none was performed after this tuning.
