# Groundhog Day Robot Repair Shop

An experiment design comparing one robot mechanic under three memory policies: no cross-job memory, a raw notebook of the last 12 turns, and structured working/episodic/semantic/procedural memory. All three will use the same OpenAI model and face the same ten repair jobs. Completion, repair steps, and actual token usage will be measured without assuming which policy wins.

**Status: runnable local prototype on the implementation branch.** The deterministic simulator, three memory policies, LangGraph orchestration, usage ledger, and animated Gradio bays are implemented. Offline demonstrations are clearly labelled; they are not evidence of model performance.

## Run locally

Use Python 3.11 or newer (verified here on Python 3.15). From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/python -c "import tiktoken; tiktoken.get_encoding('o200k_base')"
.venv/bin/python -m repair_shop.app
```

Open **http://127.0.0.1:7860** on the same computer. The server binds only to loopback, does not create a Gradio share link, and is not remotely accessible. The one-time tokenizer preparation downloads its official vocabulary; subsequent offline runs use the cache. `requirements-lock.txt` records this prototype's tested dependency environment; `pyproject.toml` gives the supported top-level ranges.

The default **Offline scripted demo** uses an observation-driven deterministic mock and makes no model calls. Choose the number of jobs, then **Start shift**. Three bays run the same fixed jobs with separate state. **Stop** prevents new calls after an in-flight request settles; its returned usage is retained. **Reset workshop** clears session memory once stopped. Every new shift starts empty. **Replay last shift** uses recorded events with no API calls. Desktop shows neighboring bays; narrow screens stack them. Reduced-motion preferences disable CSS animation.

**Live OpenAI (paid)** is an explicit opt-in. A live shift is limited to the first 1–4 jobs per bay (at most 12 jobs total); offline mode supports all ten. The full repeated evaluation proposed by the spec has not been run. The backend runs bays sequentially for auditable call limits, while each displayed bay animates its actual event state. Reloading the browser loses the UI session's replay; CLI reports are written under ignored `runs/`.

## Configuration and safety

Copy `.env.example` to `.env` only if `.env` does not already exist. Set `OPENAI_API_KEY` yourself and set `OPENAI_MODEL` to your selected API identifier. The user-selected model for this prototype is `gpt-6-luna`, verified in current official documentation and in real repair calls. It is used unchanged for all conditions and memory writes. No model substitution occurs. Never commit a real key or paste it into chat. The UI never receives it. Credentials are read only by the server-side official OpenAI client, which uses the official endpoint, disables automatic retries, and requests `store=False`. Remote tracing and Gradio analytics are disabled.

Each job has at most 12 tool calls; a non-action or incomplete response ends it unfinished. Repair responses have a 1,024 output-token limit; memory writes have a 1,600 output-token limit. Reasoning/decoding defaults are identical across repair conditions. Output usage includes the API-reported total, including reasoning tokens. There is no estimated dollar price: the till is fictional token cash. Input/output totals include memory writes; maintenance is also shown as a subtotal. Failed or uncertain requests stop the shift, with incomplete usage explicitly marked. There are no automatic paid retries.

## Design and memory

[SPEC.md](SPEC.md) preserves the approved version 1 unchanged; its original design-only status text is historical. Its PFAI references are attribution by title/page only. Repair checklists are original adaptations. No private course files or links are distributed, and no open-source license has been selected.

`world.py` holds the hidden deterministic rules. Agent inputs contain only the job ticket, permitted prior memory, current exchanges, and remaining steps. A `StateGraph` runs load → decide → execute → decide → finish → save. Fresh run/mode/job checkpoint threads and isolated store namespaces prevent cross-condition memory leakage. Scoring/event logs are not injected into model context.

- **Groundhog Day:** current-job transcript only; no cross-job store.
- **Raw notebook:** latest 12 complete action/result exchanges, including full tool results and original tickets/boundaries; the window is fixed during a job and is never summarized.
- **Four-level memory:** current-job working context plus episodic, semantic, and procedural records. One model call updates notes after each job. Validation checks schema, model/revision/source-job references, supported success, and a 1,000-token serialized note budget using fixed `o200k_base` tokenization. Invalid/oversized updates retain previous notes and still count their usage. This is a local storage budget, not a claim that the tokenizer exactly matches API billing. No embeddings, hidden-answer validation, or fine-tuning is used.

## Verification

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m repair_shop.smoke                 # free, one job per mode
.venv/bin/python -m repair_shop.smoke --live --jobs-per-mode 1  # paid, explicit
```

Tests cover all ten simulator jobs, wrong-order no-ops, revision differences, mode isolation, exact notebook windows, fresh runs, step/non-action stops, error handling, usage subtotals, invalid memory, escaped HTML, and stop/reset/replay. UI verification covers desktop and 390px mobile layouts, memory drawers, completion tables, replay, stop, reset, and repeat runs.

**Live smoke evidence (2026-10-28):** one job per mode, all three passed in 8 tool steps each. The 24 successful repair calls reported **14,770 input + 1,472 output = 16,242 tokens**. The following structured-memory request returned HTTP 400; live testing stopped without retry. That rejected request supplied no usage, so the run's accounting is marked incomplete. The maintenance request has since been changed from legacy JSON-object mode to the officially recommended strict JSON schema and covered with mocked tests, but the corrected maintenance path has **not yet been verified live**. These three jobs establish basic model/tool connectivity, not comparative memory performance. No benchmark advantage is claimed.

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
