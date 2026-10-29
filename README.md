# Groundhog Day Robot Repair Shop

A local experiment harness for comparing robot mechanics on identical repair jobs. Configure each mechanic’s model, reasoning and memory, save a versioned experiment, and compare passes, tool steps, reported tokens and estimated dollars.

The animated Gradio workshop follows actual simulator events. The free demo is scripted and makes no model calls; it is useful for checking the interface, not measuring AI performance.

## Start locally

Use Python 3.11 or later (tested on Python 3.15):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"
.venv/bin/python -m repair_shop.serve
```

Open **http://127.0.0.1:7860** on the same computer. The launcher creates a detached local process with ignored `logs/workshop.log` and `logs/workshop.pid`; it does not install a login service. After a computer restart, launch it again. For foreground development, use `.venv/bin/python -m repair_shop.app`. Reload an old disconnected browser tab after a server restart.

The server binds only to localhost; no public Gradio link is created. The first tokenizer preparation downloads its vocabulary. Dependency versions are in `requirements-lock.txt`.

## Paired evaluation harness (v2)

The new condition-based harness runs separately with `.venv/bin/python -m repair_shop.evaluation.app` on localhost port **7862**. It accepts arbitrary condition lists, independent repair/writer settings and the eight-ticket `service-v1` suite. See [the implementation guide and execution plan](docs/EVALUATION_HARNESS_V2.md) and [offline 24-attempt example](examples/evaluation-memory-pilot.json). Legacy workshop instructions below retain their original semantics and storage. No live pilot is authorized by the example.

The [October 28 live evaluation](docs/LIVE_EVALUATION_2026-10-28.md) records a bounded Luna run, matched outcomes, role usage, trace findings and proposed follow-ups. It stopped at the run-token admission guard after 46 started attempts; its partial results do not establish a general memory ranking.

The [50k job-budget follow-up](docs/LIVE_EVALUATION_50K_2026-10-28.md) completed all 72 attempts: 65 certified, seven unfinished, 1,922,632 reported tokens and $0.2340464 estimated cost. [Versioned prompt/task tuning](docs/EVALUATION_TUNING_V2.md) follows that analysis and is available as the offline **tuned-v2** preset. That initial repair-v2 preset was not run live; historical v1 tasks, prompts and examples remain unchanged.

The subsequent [memory-first combined intervention](docs/LIVE_EVALUATION_TUNED_2026-10-28.md) used repair-v3, writer-v2 and service-v2 after **107 offline tests passed**. It completed 72 attempts: **67 certified**, five compound budget failures, 1,945,605 tokens and $0.2333469 estimated. Structured memory showed repeat/transfer reuse, but no memory certified more repairs at lower overall cost. The **tuned-memory-first** preset remains offline by default. Prompt and task changes were combined, so the result does not isolate one cause.

The [controlled Sol repair comparison](docs/LIVE_EVALUATION_SOL_2026-10-29.md) changed only the repair model, keeping the Luna writer and tuned protocol fixed. Its $0.50 admission guard stopped execution at **10 certified, one interrupted and 61 unattempted** positions ($0.4415131 estimated). The three common early tickets had the same action counts as tuned Luna; later exceptions and compound work were not reached. [The world and task explainer](docs/EVALUATION_WORLD.md) describes the machinery, seven tools, hidden state and independent certification.

The [authorized Sol continuation](docs/LIVE_EVALUATION_SOL_EXTENDED_2026-10-29.md) preserved that interrupted attempt and all prior charges, then executed only the 61 untouched positions under a $10 combined ceiling after **120 offline tests passed**. Final coverage: **68 certified, three job-token failures, one preserved interruption, zero unattempted**; 1,807,233 tokens and $3.765312 estimated. Structured and no memory both certified 24/24; structured used 30 fewer actions but 38.8% more tokens and cost 17.8% more. Matched Luna comparisons and interruption-history sensitivity data are included.

## Put an experiment together

1. Name the experiment and add notes or a hypothesis. Choose a task set, jobs per mechanic and repeated shifts. The selected prefix is shown as “N of M jobs”; **Select all jobs in this task set** explicitly selects the full suite. Changing task sets preserves the chosen count where possible.
2. Click a robot to edit that mechanic. Choose its model, reasoning, memory policy, notebook window, structured-note budget, step limit and output-token caps. Select **Apply mechanic settings**. The displayed experiment summary lists repair and memory output-token caps together for every mechanic.
3. Use **Save as new experiment** for a new configuration identity. **Save new version** appends a version to the loaded configuration; previous versions stay available. Loading an older version is allowed; saving over a newer version is refused so concurrent edits cannot silently overwrite it.
4. Leave **Use OpenAI (paid calls)** unchecked for a free demo. Start the experiment explicitly when ready. Paid runs use the model selected for each mechanic, including that mechanic’s memory writes.
5. Review passes and unfinished attempts alongside steps and cost. Open **Saved runs and shareable reports** to revisit results or create HTML, JSON and CSV reports.

A **job** is one ticket. Each mechanic makes one **attempt** at each selected job. A **step** is one tool call. A shift covers all selected jobs and all three mechanics, in ticket order. Repeated shifts start with fresh memories. For example, 4 jobs × 3 mechanics × 2 repeated shifts produces 24 attempts, each with its own step cap. To study accumulating memory, increase jobs within a shift; repetitions measure fresh starts.

The original ten-job baseline remains selectable. The new **diagnostic-v1** set requires targeted measurements, compound repairs, power interlocks, a spare-fuse budget and revision-specific cooler behavior. Similar symptoms can have different causes. There are no manuals in this release. Read the [task author guide](repair_shop/tasks/README.md) for all ten scenarios and [task definition contract](docs/TASK_DEFINITION_SPEC.md) for new suites and future manual retrieval.

## Saved versions and results

The ignored local database is `runs/experiments.sqlite3`. Each run captures its exact configuration, task version, fingerprint and seed. Changing settings or saving a new version cannot change past results. Model settings remain separate from credentials.

A pending-request marker is checkpointed before each model call, and returned API usage is checkpointed before another request; completed attempts and final status are also saved. The app never resumes a paid run automatically. A stored “running” status after a restart may mean the process stopped during a request: known usage is retained, but in-flight usage may be unknown. Loading a stored running checkpoint creates a recovered view with an interrupted attempt and known steps/usage, without changing the stored row or resuming execution. Legacy checkpoints use only recorded events; missing observations and usage are never invented. A passing test already recorded before interrupted memory maintenance remains a pass with an interruption warning. Execution outcome, checkpoint-saving warnings and report-export warnings are separate; an export failure cannot overwrite the original API error. Earlier prototype reports remain in `runs/`; they are not automatically imported into the new database.

**Stop** waits for an in-flight response to settle before starting no further requests. **Reset workshop** clears the displayed session after it stops. **Replay displayed run** uses saved events and makes no model calls. Loading saved results constructs no API client. Mechanic names and result rows stay tied to the recorded run even if you edit the next experiment.

Reports are local files, not public links. The HTML works without a server and includes memory notes and exact settings. JSON includes the configuration, fingerprint, results and known usage; it omits raw response identifiers and detailed event logs. CSV includes repetition, model, memory, reasoning, step limits and attempt outcomes. Review your annotations and notes before sharing. No report serializes the environment or model client.

Saved configurations can also run from the command line:

```sh
.venv/bin/python -m repair_shop.experiment list
.venv/bin/python -m repair_shop.experiment run --config CONFIG_ID --version 1
# A saved paid configuration requires explicit opt-in:
.venv/bin/python -m repair_shop.experiment run --config CONFIG_ID --version 2 --live
```

## Models, bounds and accounting

Place the key yourself in the ignored `.env` file at the repository root, using `.env.example` only if `.env` does not already exist. Never commit the key or paste it into chat. The official OpenAI client alone loads it server-side. It uses the official endpoint, disables retries and requests `store=False`. Remote tracing and Gradio analytics are disabled.

The model dropdown lists `gpt-6-luna`, `gpt-6-sol` and `gpt-6-astra` from current official documentation; listing a model does not confirm account access. The UI defaults to Luna. `OPENAI_MODEL` remains a fallback for legacy command-line smoke calls; saved UI experiments use their explicit per-mechanic choices. Unsupported model/reasoning pairs are rejected; no model substitution occurs. “default” omits the reasoning setting and uses the provider default.

Limits are configurable within bounded ranges: 1–40 tool steps, 0–100 retained notebook exchanges, 128–8,000 structured-note tokens, 128–4,096 output tokens per repair/memory request, and 1–10 repeated shifts. Jobs range from 1 to the chosen suite’s size. The whole-run token limit is checked after every returned response; one in-flight request can exceed it. The default remains 12 steps, 12 notebook exchanges, 1,000 note tokens, 1,024 repair output tokens and 1,600 memory output tokens.

Only a passing simulator test counts as success. A failed test uses a step and can be followed by further repairs. A non-action/incomplete response or the step cap ends an attempt unfinished. “Run complete” means all scheduled attempts ended, not that every repair passed. Errors stop the run; uncertain usage is marked rather than treated as zero. Output usage includes reported reasoning tokens. Memory writes consume tokens and cost but no repair steps.

Luna dollar estimates use official standard uncached text rates checked 2026-10-28: $0.10/M input and $0.50/M output, with the documented long-context multiplier. Caching, cache-write premiums, region/service-tier adjustments and taxes are excluded. Other models currently display N/A for cost. Demo runs display $0. This is an estimate, not a billing invoice.

## Memory and task isolation

The LangGraph loop is load → decide → execute → decide → finish → save. Checkpoint threads include run, repetition, bay and job. Store namespaces include run, repetition and bay. Bay identity is separate from memory policy, so all three bays can use the same policy with different models if desired.

- **Groundhog Day:** current-job context only; no cross-job records.
- **Raw notebook:** the configured number of complete action/result exchanges, without summarization. A window of zero retains nothing between jobs.
- **Four-level memory:** current-job working context plus episodic, semantic and procedural records. A separate call updates notes. Validation checks schema, family/revision/source references, supported successes and the configured serialized token budget. Invalid notes are rejected; previous notes survive and returned usage still counts.

The note budget uses `o200k_base` as a fixed local measurement, not an API billing claim. Tool observations are the only world evidence given to models. Private scoring state and other bays’ notes do not enter their prompts.

[SPEC.md](SPEC.md) preserves the original approved design; its design-only language is historical. [EVALUATION_ROADMAP.md](EVALUATION_ROADMAP.md) preserves earlier proposals. This release implements configuration and a diagnostic suite while deferring manuals. No private course material or local personal paths are published, and no license has been selected.

## Verification and limitations

```sh
.venv/bin/python -m pytest -q
```

Offline tests cover both complete task sets, diagnostic constraints, memory isolation, repetition resets, configurable limits, token stops, safe exports and SQLite version/snapshot persistence. Browser checks cover the mechanic editor, saved versions, repeated demo runs, stop/reset, replay, report export and mobile layout.

The UI has three bays and uses ordered ticket prefixes. There is no arbitrary uploaded task code, automatic task generation, cross-run memory or confidence-interval analysis. The diagnostic suite is harder by construction, but whether it separates model/memory approaches needs a controlled evaluation. Free demos and bounded integration smoke tests do not establish rankings.

Prior implementation smoke tests exercised five repair jobs and 42 successful calls, reporting 32,003 known tokens. An earlier rejected memory request had unavailable usage; it is not silently counted as zero. Upgrade smoke (2026-10-28): three diagnostic-v1 attempts on Luna all passed in six tool steps. Nineteen successful calls reported 14,909 input + 1,482 output = 16,391 tokens, including 1,246 maintenance tokens (estimated $0.0022319). The structured-memory update was rejected by validation and previous notes were retained; the precise validation reason was not recorded by that version. The current code records a safe rejection reason and clarifies that note “model” means robot family, not AI model. Those changes passed mocked tests but were not retested live because the three-attempt authorization was exhausted. This smoke verifies repair integration, not successful note retention or comparative performance. User-run experiments are separate from development smoke tests.

## Official documentation checked

Checked **2026-10-28 (UTC)** against the current official documentation, rather than older tutorials. Installed package versions are recorded in `requirements-lock.txt`; the integration limits above distinguish mocked and real validation.

| Topic | Official source | Design implication |
| --- | --- | --- |
| StateGraph, state, nodes, edges | [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) | Define the repair loop with explicit state and conditional termination. |
| Model/tool loop | [LangGraph quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart) | Alternate decisions and tool results; adapt its pattern to the selected OpenAI model and the spec's one-call-per-turn rule. |
| Persistence split | [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Checkpoints retain thread state; stores hold cross-thread data. |
| Checkpoint isolation | [Checkpointers](https://docs.langchain.com/oss/python/langgraph/checkpointers) | Use a fresh mode/run/job thread ID; do not accidentally carry prior-job transcripts forward through checkpoints. |
| Cross-job memory | [Stores](https://docs.langchain.com/oss/python/langgraph/stores) | Isolate records by run and condition; only permitted memory crosses job boundaries. |
| In-process primitives | [Memory](https://docs.langchain.com/oss/python/langgraph/add-memory) | `InMemorySaver` and `InMemoryStore` support the planned in-process demo; they are not disk persistence. |
| Shop layout | [Gradio Blocks](https://gradio.app/docs/gradio/blocks) | Plan a Python-defined three-bay interface. |
| Visual component | [Gradio HTML](https://gradio.app/docs/gradio/html) | Plan an HTML/CSS presentation of logged repair events. |
| Event updates | [Streaming outputs](https://gradio.app/guides/streaming-outputs) | Generator outputs can update the display as events are replayed. |

The isolation rules and experimental controls above are project design decisions applied to these documented primitives. Recheck the official sources before writing implementation code.

Additional implementation references checked 2026-10-28: [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [function calling](https://developers.openai.com/api/docs/guides/function-calling), and [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs). The maintenance request uses the documented strict JSON-schema format.

UI/report update references checked 2026-10-28: [OpenAI API pricing](https://developers.openai.com/api/docs/pricing), [GPT-6 Luna pricing](https://developers.openai.com/api/docs/models/gpt-6-luna), and [Gradio download controls](https://gradio.app/docs/gradio/downloadbutton).

Experiment configuration references checked 2026-10-28: [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol), [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra), and [Gradio HTML events](https://gradio.app/docs/gradio/html). The model choices and reasoning options follow these official pages; live verification is limited to the explicitly selected smoke-test model.

## Learning-focused evaluation upgrade

On this implementation branch, **Learning: 32 repairs with delayed repeats** adds costly calibration discovery, immediate and delayed reuse, revision changes, marked replacement-module exceptions and cable-only controls. Select up to 32 jobs in one shift. [The evaluation plan](docs/LEARNING_EVALUATION.md) explains the sequence and what each comparison can establish.

New experiments default to **Merge validated records (v2)** for structured memory. Valid older notes survive omitted updates; valid new records survive an invalid sibling citation. Budget evictions remain deterministic and visible. The mechanic drawers expose which past jobs were supplied and which notes were accepted, rejected or removed. A new phase table compares discovery, repeats, controls and exceptions without claiming causal memory use.

Old saved configurations keep **Replace all notes (legacy v1)**. To use the new retention behavior, change that field on the structured mechanic and save a new configuration version. Past results and task fingerprints remain intact. This upgrade was validated offline and with mocked API responses; no new paid model tests were run.
