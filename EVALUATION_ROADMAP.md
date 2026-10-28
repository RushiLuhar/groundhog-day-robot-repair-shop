# A harder, versioned evaluation set

The current ten jobs remain **baseline-v1**, unchanged. They establish tool correctness and basic memory reuse. The following is a proposal for **challenge-v2**, not a claim that harder jobs are implemented or that current results generalize.

Keep the simulator deterministic and the task set fixed within an experiment. Configure each mechanic independently by model, reasoning setting, memory policy/budget, and tool budget; record the complete configuration in every report. Change one factor at a time for interpretable comparisons. Do not give one bay extra observations or a different job order.

## Recommended first additions

| Challenge | Concrete example | What it measures |
| --- | --- | --- |
| Ambiguous symptoms | Overheating could come from coolant order, a loose thermal cable, or a fuse. A targeted diagnostic distinguishes them; the initial ticket does not. | Information gathering rather than guessing the recipe |
| Delayed repeats | Return an early customer after enough intervening work to exceed the 12-exchange notebook. | Retention and retrieval; do not assume structured memory will win |
| Revision exceptions | The same chassis returns with a revised controller requiring a different sequence. Old repair history remains true for the old revision. | Conditional knowledge and resisting overgeneralization |
| Compound faults | Two faults produce overlapping symptoms. Fixing one improves a reading but does not pass the final test. | Verification and multi-step diagnosis |
| Scarce parts / costly diagnostics | Give each job a fixed parts allowance and known diagnostic costs. Wasteful replacements can make a job infeasible. | Repair quality versus resource efficiency |
| Unreliable customer history | A ticket includes a customer's unverified “last time a fuse fixed it” claim, labelled as hearsay. Diagnostics can contradict it. | Evidence provenance and correction of bad assumptions |

Start with ambiguous symptoms, delayed repeats, and revision exceptions. These directly test the intended memory differences without simultaneously changing too many mechanics. Add resource management later as a separate difficulty tier.

## Suggested ten-job shape

1. Learn an unfamiliar fault with informative diagnostics.
2. Introduce a second chassis with a different repair order.
3. Same symptom, different cause.
4. Repeat job 1's fault to test early reuse.
5. Introduce a compound fault and require a final functional test.
6. Unreliable customer history contradicts measurements.
7. More intervening work with an unrelated fault.
8. Delayed return of job 2's chassis.
9. Revised controller invalidates the old sequence for this revision.
10. Return of the revised controller to test correction and retention.

The exact fixtures, observable clues, budgets, and scoring need to be frozen together before comparing runs. Validate every job with a deterministic oracle: at least one successful tool sequence must fit the budget. Keep ground-truth fault state and oracle solutions outside agent-visible context.

## Score more than pass rate

Report passes, unfinished jobs, invalid actions, diagnostic and part costs, tool steps, elapsed time, API input/output tokens, memory-write overhead, and estimated USD. Keep the denominators and unattempted jobs visible. Measure steps on successful jobs alongside failures; quitting early must never look efficient. Compare early versus delayed repeat performance and revision-transfer mistakes. API errors are infrastructure failures, not evidence that a model cannot repair the robot.

Use paired runs on the same fixtures and fixed seeds. Report individual runs and uncertainty across repetitions before making rankings. Version the task set and scoring; never blend baseline-v1 and challenge-v2 results into one leaderboard. A few smoke tests establish integration, not benchmark performance.

The next harness iteration can represent each bay as a configuration object and a run manifest. Cross-model comparisons must specify supported reasoning settings explicitly; a provider default is not necessarily equivalent across models. Keep the existing shared-model three-memory comparison available as a preset.
