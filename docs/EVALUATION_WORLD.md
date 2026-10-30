# What the repair evaluation actually simulates

This is a small deterministic software world, not a robotics physics engine or a client case study. The robot workshop is a presentation for a common agent workflow: inspect evidence, distinguish causes, change state through tools, verify the outcome, and decide which prior knowledge applies. It provides a controlled place to measure memory, prompts, model choice, reasoning effort and resource limits. No coffee-related task or performance measure exists in the harness.

The current live sequence is `service-v2 / standard-v1`. [The world implementation](../repair_shop/evaluation/service.py), [versioned task changes](../repair_shop/evaluation/service_v2.py) and [shared prompts](../repair_shop/evaluation/models.py) are the source of truth. The earlier service-v1 sequence remains available for its historical results.

## The machine

Each ticket concerns a unit with a temperature sensor, installed calibration settings, a cooling mechanism, a cable and a power switch. All eight tickets have the same public complaint: **intermittent shutdown under load**. That complaint is deliberately insufficient to identify the cause. A unit can have incorrect sensor calibration, genuine overheating from restricted cooling, an intermittent cable, multiple problems, or no fault requiring repair.

The sensor's raw response follows `s = g × T + b`. Its physical gain `g` and bias `b` are initially unknown to the repair agent. The displayed temperature is `(s − installed_bias) / installed_gain`. Writing calibration changes the display calculation, never the actual temperature. A plausible display therefore does not establish physical safety.

For a cold diagnosis, the agent can take a low and high reference sample. Each gives the actual reference temperature and raw sensor value; these two points determine gain and bias. For example, readings 70 at 30 degrees and 150 at 70 degrees imply gain 2 and bias 10. The agent must derive that relationship from observations; the logger does not calculate it. Once supported by evidence, it can be reused across chassis when the **sensor component, revision and origin** match. The chassis/customer label is not the calibration key; `inspect` supplies the current sensor markings.

Cooling faults are separate. Restricted cooling means a true temperature of 80 degrees; clear cooling means 40. Safety requires at most 60. Cooling service consists of align, vent and seal, with interlocks determining whether align or vent must come first. Both must precede seal. The restriction clears only when service is sealed. A healthy, untouched cooler requires no such work. An interlock constrains an operation; its existence is not evidence that cooling service is needed.

## Seven tools, with real state changes

| Tool | What the agent supplies | What it learns or changes |
| --- | --- | --- |
| `inspect` | No arguments | Chassis, component/revision/origin markings, installed gain/bias, indicated temperature, power and visible cooling work. Installed values are not guaranteed to be correct. |
| `sample_sensor` | Low or high level | Raw sensor reading and independent reference temperature at 30 or 70 degrees. Requires power on; installed calibration does not affect these readings. |
| `probe` | Thermal, continuity or interlocks | Thermal directly reports clear/restricted airflow and true reference temperature. Continuity reports steady/intermittent wiring. Interlocks expose current ordering constraints. These observations are intentionally diagnostic. |
| `power` | On or off | Changes and reports power state. |
| `operate` | Align, vent, seal or reseat cable | Attempts physical work, requiring power off. Invalid ordering or unnecessary cooling work returns a rejection and still costs an action. Reseating fixes the cable. |
| `calibrate` | Integer gain 1–4 and bias −20–20 | Installs settings with power off. Acceptance means the write happened, not that it was correct. |
| `test` | No arguments | Independently checks the current unit and returns pass/fail. In v2 a power-off test explicitly reports its unmet power precondition. Other failures do not identify which fault remains. |

Every tool invocation is one repair step, including inspection, a rejected operation and a failed test. The model must choose one tool per response. It has 20 steps in the measured runs; a response with no valid single action ends the attempt unfinished. Memory maintenance consumes model tokens and dollars but is not a repair step. The deterministic observation logger makes no model call.

## What counts as success

Only a passing `test` certifies a repair. The simulator checks all of the following independently of the agent's explanation: power is on; calibration is accurate at both reference temperatures; true temperature is safe; cable continuity is steady; and any started cooling work has been sealed. Correcting the displayed temperature cannot hide real overheating. A successful calibration write, completed-looking work, a model's claim, or reaching a budget limit cannot substitute for certification.

The simulator stores the true physical sensor relationship and fault flags privately. Those fields and author-facing task labels are never placed in the model context. The agent receives the public complaint/rules and actual tool observations. Some tools deliberately expose strong evidence—particularly thermal/continuity probes and reference samples. This is not a test of guessing unobservable faults. It tests choosing, combining and reusing evidence while respecting state and ordering constraints.

## The eight tickets

This table is an **author explanation of the fixtures**, not a table sent to the agent.

| Position | Situation in service-v2 | Decision being tested |
| --- | --- | --- |
| 1 | Factory R1 sensor with incorrect installed calibration | Discover the physical relationship, correct it and certify. |
| 2 | Healthy unit with the same sensor relationship | Avoid unnecessary service; applicable evidence can avoid remeasurement. |
| 3 | Same sensor, different installed settings, plus a loose cable | Reuse calibration without assuming the entire earlier repair is sufficient. |
| 4 | Same complaint and correctly calibrated sensor, but restricted cooling | Distinguish a physical cooling fault from a sensor-calibration problem. |
| 5 | Same factory component on a different chassis | Transfer evidence by component/revision/origin rather than customer name. |
| 6 | Marked replacement sensor with a different relationship | Recognize the exception and measure instead of blindly applying the factory rule. |
| 7 | Factory sensor returns, initially carrying replacement-like settings | Preserve the original rule alongside the exception; installed settings are not component identity. |
| 8 | Novel R3 sensor, real heat, loose cable and different cooling order; display initially looks normal | Diagnose a new relationship, detect independent physical faults, obey ordering and finish certification. |

Every ticket can be solved from current observations without cross-job memory. Memory can save information-gathering actions on applicable repeats, but it also adds input and maintenance cost. New revisions and replacements require fresh evidence. Compound work can still run out of allowance before the final test even when earlier memory was useful.

## What varies between agents

The chosen comparison uses three conditions on exactly the same ordered tickets: no cross-job history; a rolling window of whole literal observation entries; and typed episodic/semantic/procedural records maintained by one job-end writer. All receive the same current-job raw results and factual logs. Structured records include applicability and source IDs. Validation checks those IDs and passing-test provenance, not the truth of every sentence.

The deterministic logger renders the action, observed result and explicit returned status. It does not diagnose, solve calibration equations or inspect hidden state. A model repair agent or memory writer may infer relationships from the evidence it receives. Retained evidence, evidence actually supplied, behavior consistent with reuse and measured benefit are separate observations.

The measured configuration uses 40 rolling entries, 3,000 retained memory tokens and a 2,000-token supply budget. Whole entries/records are selected within those limits, so the entry count is a ceiling rather than a promise of 40 supplied entries. Each condition gets fresh memory for every repeated shift. The harness accepts arbitrary condition lists; three is this protocol's choice, not a requirement of three visual workshop bays.

The task is a controlled proxy for evidence-based tool work. It supplies no claim that these eight synthetic repairs represent any particular client's workflow, or that a few runs establish which architecture is generally best.
