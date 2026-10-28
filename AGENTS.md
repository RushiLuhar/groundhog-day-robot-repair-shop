# Working on Robot Repair Shop

This is a localhost experiment harness with a Gradio workshop and LangGraph agent loops. Keep the original baseline available. Do not treat demo results or a few smoke tests as evidence that one model or memory approach is better.

## Setup and preview

Use Python 3.11 or later and an isolated environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python -m pytest -q
.venv/bin/python -m repair_shop.serve
```

The preview is http://127.0.0.1:7860. `serve` starts a detached task-local process; it does not install a service. The foreground command is `.venv/bin/python -m repair_shop.app`. Check the UI and port before restarting; do not interrupt an active paid run. Use Stop and wait for returned usage to settle. Keep the listener bound to localhost and never enable a public share link without explicit authorization.

## Secrets and paid calls

Only the owner edits `.env`, containing `OPENAI_API_KEY` and optional `OPENAI_MODEL`. Never print, inspect, copy, commit or send its contents. `.env.example` contains placeholders only. The official OpenAI client loads the key server-side. Do not add tracing, credential management, alternate endpoints, public deployment or new access.

Default to the free demo and mocked tests. Paid testing requires explicit scope; obey the approved attempt ceiling, model, output caps and run token limit. Never substitute a model silently or automatically retry an API failure. A timeout can have an unknown bill; preserve known usage and report the uncertainty. The total-token stop is checked after returned usage and may overshoot by one in-flight request.

## Configurations and results

Click a robot to edit its model, reasoning, memory and limits, then Apply mechanic settings. Experiment fields choose the task set, jobs, repeated shifts, notes and token limit. Save new version appends a version. Save as new experiment starts a separate configuration identity. Past runs preserve their configuration snapshots.

The local database is `runs/experiments.sqlite3`. Reports, logs, SQLite sidecars and the database are ignored. Do not commit them. No run resumes automatically after a crash. A stored “running” status after restart means execution may have been interrupted; inspect known usage before any explicit new run.

```sh
.venv/bin/python -m repair_shop.experiment list
.venv/bin/python -m repair_shop.experiment run --config CONFIG_ID --version 1
# Only when authorized, for a version saved with OpenAI enabled:
.venv/bin/python -m repair_shop.experiment run --config CONFIG_ID --version 2 --live
```

Each bay attempts every selected job once per repeated shift. All bays get the same ordered job prefix. Memory persists between jobs within one shift, never across repetitions or runs. A tool call is one step; memory writes consume tokens but not repair steps. A final passing test is the only success signal.

## Task extensions and validation

Read `docs/TASK_DEFINITION_SPEC.md` and `repair_shop/tasks/README.md` before adding tasks. Keep `baseline-v1` and its fixtures unchanged. Register trusted Python task implementations explicitly; do not execute uploaded code. Hidden scoring state must never enter model context or public observations. Do not publish private course materials or local personal paths. Manuals remain a future extension.

Run simulator, engine, model, storage and reporting tests after behavior changes. Verify the browser at desktop and mobile widths, including configuration round trips, task selection, stop/reset, replay, saved run loading and report export. Distinguish these offline checks from live tests in the final report.

Inspect the complete diff and staged files for secrets, private data, unrelated edits and generated output. Work on the implementation branch, update its existing PR, and leave main unmerged for review. Never force-push. Preserve user changes.
