# Paired evaluation harness v2

Implementation of [proposal v2 and its execution plan](https://chatgpt.com/space/page_c1b81db8c6a08191aa863a89989de4e2), based on merged main `c38224058838b9c8d025fbf0fcdee7279f0118e7`. The legacy workshop, task fixtures, configuration schema and database remain unchanged. There is no implicit migration. Use its original entry point to read or replay legacy experiments.

## Local entry point

After the normal isolated Python installation:

```sh
.venv/bin/python -m repair_shop.evaluation.app
```

This is a foreground localhost-only UI on port **7862**. It uses `runs/evaluation.sqlite3` and `runs/evaluation-reports/`, separate from the legacy workshop on port 7860. It installs no service and opens no public link. Do not restart an active experiment. Stop waits for returned usage; reset is allowed only after execution ends. Paid work requires a saved/explicit configuration with `live: true` plus the UI paid opt-in and a separately approved run scope. This implementation and its example authorize no paid pilot.

The JSON editor is the authoritative configuration. Validate displays every condition's independent repair and writer model, effort, prompt, output cap, stored/supplied memory budgets, rolling entry limit, tool limit and combined job token allowance. Start validates the current text and snapshots it. Configuration versions append; loading a version does not run it. Memory, reasoning, model and output-cap presets are available. Two-condition presets execute exactly two conditions. The model preset disables the USD fuse explicitly because the existing verified pricing table does not price every selectable model; its token fuse remains active.

## Execution plan and acceptance

| Milestone | Implementation | Offline acceptance |
| --- | --- | --- |
| Condition runner | `evaluation/config.py`, `runner.py`; no visual bay identity | One, two, three and four conditions; paired tickets, repetitions, immutable manifests, unsupported settings rejected |
| Logs and memory | `observations.py`, `memory.py`, `models.py` | Literal results, source IDs, malformed/oversized log errors, complete-entry eviction, partial-job markers, typed notes, invalid citations, omissions and bounded supply |
| Eight-ticket world | `evaluation/service.py`, explicit `tasks.EVALUATION_SUITES` registry | Cold paths, healthy control, transfer, replacement, old-rule return, novel ordered compound repair and independent certification |
| Accounting and inspection | `runner.py`, `storage.py`, `reporting.py`, `app.py` | Role tokens/cost, stop/caps/failures, pending-call recovery, errors after certified pass, immutable versions, current UI lifecycle and trace exports |
| Delivery | Offline test suite and isolated browser preview | Preserve all legacy tests; inspect desktop/mobile, stop/reset/replay, saved loading and exports; keep code local pending publishing authorization |

## Frozen world: service-v1 / standard-v1

The world models a sensor controller, cooling loop and cable. Every ticket has the same complaint. Inspection exposes component/revision/origin, chassis, installed calibration, indicated temperature, power and visible work. No scorer phase labels or private fixtures are sent to either role.

Sensor raw response is `s = g*T + b`. Separate low/high samples expose raw values and reference temperatures 30 and 70. Displayed temperature is `(s - installed_bias) / installed_gain`. The repair agent derives gain/bias; the logger does not. The independent test checks calibration at both references, true temperature at or below 60, cable continuity, power and completed mechanical work. Changing the display cannot repair genuine overheating.

| Ticket | Author-facing case | Factory/exception relationship |
| --- | --- | --- |
| 1 | Discover factory calibration | TS-7 R1 factory |
| 2 | Healthy unit | Same component and correct initial settings; no repair needed |
| 3 | Different initial settings | Same underlying sensor relationship |
| 4 | Same complaint, restricted cooling | Correct sensor; thermal diagnosis matters |
| 5 | Component transfer to Mint chassis | Same TS-7 R1 factory sensor |
| 6 | Marked replacement | Same revision, different origin and calibration |
| 7 | Original factory module in Violet chassis | Do not generalize replacement evidence |
| 8 | Novel R3 plus cooling and cable faults | New calibration; align-before-vent interlock, then seal; reseat cable |

Both vent and align must precede sealing. R1 requires vent first; R3's observable interlock requires alignment first. Service and calibration require power off. All eight cold paths fit the common 20-step cap; the scripted compound path uses 14 steps. Fixture changes require a new version/fingerprint, not silently replacing this suite. Additional variants are deferred.

## Context and memory semantics

Every repair request receives the current ticket, remaining tool/job limits, current-job raw tool results and literal logs, missing-log markers, and only its policy's admitted prior memory. The raw evaluation ledger is never a cross-job backup. The deterministic renderer preserves the action/result with a source ID and job boundary, adds only explicitly returned status, rejects unsupported schemas and bounded-length violations, and makes no API calls. Its text still costs input tokens when later supplied.

- **None:** no cross-job memory store is populated. Current-job context remains available.
- **Rolling:** newest whole entries, unchanged, within the entry count and stored-token ceiling; supplied context has its own ceiling. Eviction never truncates a field or entry. The supply audit and repair-context boundary metadata mark jobs whose older entries are absent. Boundary metadata is separate from the evidence-size ceiling and contributes to actual request input usage. Defaults (40 entries, 3,000 retained tokens, 2,000 supplied tokens) were not tuned to delete one specific lesson.
- **Structured:** one job-end writer gets the condition's logs, missing-entry markers, previous records and source identity/pass metadata. It never gets raw historical events or private scoring state. Episodic/semantic/procedural records have component/revision/origin applicability, exact source IDs and tentative/test-supported/disputed status. Procedural or test-supported claims require a cited passing test. Validation does not prove semantic truth.

Structured omission retains prior records. Exact statements deduplicate toward their most recent evidence; records sort by newest source ordinal, then procedural/semantic/episodic priority, then stable hash. Whole-record retention and supply enforce separate token ceilings. Audits report supplied, accepted, rejected, omitted, duplicate, evicted and retained IDs. The trace preserves the bounded writer response, including rejected or incomplete candidates. Contradictory statements can coexist; semantic correction and causal-use grading remain human review tasks. Writer usage is counted even when its output is rejected. Writer settings stay fixed in the repair-model/reasoning/output-budget presets.

Ticket order is identical for all conditions. Condition order rotates by one across fresh repetitions, recorded explicitly in the manifest. Memory never crosses condition, repetition or run boundaries. A shared run fuse can still cause unequal exposure; reports preserve scheduled, started, unattempted and failure denominators and discourage ranking partial runs.

## Limits, accounting and recovery

Response output caps apply to individual role calls, including reasoning output. The combined job allowance sums returned repair and writer input/output tokens. Retention/supply ceilings control context size, not API usage. Run token and estimated-USD fuses are separate, include both roles, and check before new requests and after returned usage. Any returned request can overshoot a remaining allowance. USD fuses require a known dated rate for every active model; unsupported combinations fail before clients or requests. Unknown rates are N/A, never invented zero prices. Existing pricing caveats apply.

Pending requests are checkpointed before invocation. Stop during preparation cancels the call; stop while a call is in flight records returned usage before ending. Unknown request usage remains explicit, with no retries or automatic resume. Recovery makes a read-only interrupted view of abandoned checkpoints, preserving known steps and certified passes. All attempts are scheduled upfront, so an interrupted started attempt cannot disappear into “unattempted.” Memory-writer or logging failure after a passing tool test does not revoke the physical pass; its separate error is shown. Export errors never replace execution errors.

Elapsed execution and per-request time exclude replay delays. They include local runner/persistence overhead and are not claimed as model-only latency. No synthetic weighted service currency is introduced.

Manifests snapshot complete conditions, ordered tickets and condition order by repetition, task fingerprint, source commit/dirty flag, prompt texts, tools/public instructions, logger/memory/supply/consolidation versions and dated pricing. HTML/JSON/CSV exports support raw event → log → retained evidence → supplied evidence → subsequent action → independent outcome inspection. Record audit coverage and disagreements externally; no automated semantic grader is claimed.

## Pilot gate and limitations

`examples/evaluation-memory-pilot.json` is an **offline** 8 × 3 = 24-attempt configuration. It proposes, but does not authorize, a later live pilot. Validate exact model/effort, role caps, job/run allowances and spend envelope with the owner before live use. No 648-run plan, vector retrieval, manuals, noisy sensors, additional reflection role or learned retrieval is included.

Scripted successes establish simulator feasibility and harness behavior. They do not predict model behavior or establish memory superiority. In the default offline demonstration, rolling and structured memory can save the same actions on repeats; structured memory has no guaranteed advantage and a live writer can cost more or introduce errors. One small pilot cannot establish general rankings or significance. The intended next step is representative trace review, then a bounded choice of another experiment.

## Final offline acceptance, 2026-10-28

The final review covered the complete change from merged main and the proposal v2 acceptance criteria. It corrected per-attempt unknown-usage accounting during recovery (including a pending writer after a certified pass), retained writer candidates for trace review, exposed partial rolling-job boundaries to the repair agent, snapshotted numeric pricing, and synchronized export retry status. The UI now identifies the recorded configuration/run, selects the newly finished run in saved results, and scrolls wide settings tables on mobile.

**96 tests passed**, including all 69 legacy tests and 27 v2 cases. Test processes disabled dotenv loading and socket connections; legacy export paths were redirected to temporary directories. Two benign pytest assertion-rewrite warnings concerned already-imported dependencies. No live responses or billing were tested.

Browser verification used the production Gradio callbacks at **1280 × 900** and **390 × 844**, a temporary SQLite database/export directory and injected scripted agents. Paid clients were disabled. A small artificial delay made Stop/Reset observable; specially named temporary fixtures simulated token counts, truncation and API/writer failures. These injected counts are test data, not measured API usage.

| Browser flow | Observed result |
| --- | --- |
| Three memory conditions, eight tickets | 24/24 certified; 77/67/67 steps; zero model calls. This verifies the scripted mechanics, not a memory ranking. |
| Two reasoning conditions, eight tickets | Exactly 16/16 certified; no third condition. Writer settings remained fixed. |
| Two conditions, two tickets, two repetitions | 8/8 certified; first ticket repeated its cold path; condition order rotated. |
| Configuration persistence | Saved v1, edited/saved v2, restored unchanged v1; both versions remained after preview restart. |
| Stop/reset/repeated start | In-flight return settled; interrupted attempt and unattempted remainder remained distinct; reset returned to Ready and a new run got a new identity. |
| Trace/replay/history/export | Inspected supplied calibration and exact source IDs; replay made no calls and retained execution time; saved results loaded after restart; HTML/JSON/CSV exports worked. Export during execution was rejected. |
| Simulated API failure | Error shown immediately; known 210 tokens retained, one unknown request and one unattempted ticket. No retry. |
| Simulated run-token limit | One returned 210-token request crossed the 128-token limit; its tool action remained recorded; next ticket was unattempted. |
| Simulated output truncation | Two attempts unfinished with zero tool steps; neither was certified. |
| Simulated post-pass writer failure | Certified repair retained alongside writer/infrastructure error and unknown usage. |
| Tool-step limit | Both selected conditions ended unfinished after one action. |

The original workshop and its legacy data were not used for browser validation. Only the temporary port-7862 preview was started; it is stopped after verification. No paid run, push, PR, merge or deployment is part of this acceptance record.

## Authorized live protocol and request admission

The subsequent owner-authorized exploratory run is frozen in `examples/evaluation-live-2026-10-28.json`: three fresh shifts of the unchanged eight-ticket suite, three memory conditions, Luna with explicit medium reasoning, 2,048 output tokens for both roles, and the original memory/job/step limits. It permits at most 72 attempts and stops at 1,000,000 returned tokens or $1 estimated standard-price spend. This file records that run's approved scope; it is not standing authorization for later paid runs.

`request_admission_policy: conservative-bytes-v1` additionally reserves the next text request before sending: serialized UTF-8 request bytes plus 4,096 tokens of framing/schema allowance, and the full configured output cap. Both token and estimated-USD checks use that reservation. This deliberately overestimates typical text inputs; it is not provider-certified counting. The manifest and request ledger record the policy/reservations. A returned usage bound violation stops further requests without hiding the returned usage. Unknown usage also stops execution, without retries. Legacy v2 configurations that omit this field retain `returned-usage-v1` semantics.

Live requests explicitly select `service_tier=default`, preserving the standard pricing assumption; the ledger records returned model, service tier, cached-input count and reasoning-output count when supplied. Pricing was rechecked against the [official Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna); the [Responses reference](https://developers.openai.com/api/reference/cli/resources/responses/methods/create) documents standard processing. Estimates retain the existing cache/regional/tax caveats. No prompts, task fixtures or memory rules were tuned before this run. The added admission tests bring offline coverage to **99 passing tests** before paid execution.
