# Groundhog Day Robot Repair Shop

An experiment design comparing one robot mechanic under three memory policies: no cross-job memory, a raw notebook of the last 12 turns, and structured working/episodic/semantic/procedural memory. All three will use the same OpenAI model and face the same ten repair jobs. Completion, repair steps, and actual token usage will be measured without assuming which policy wins.

**Status: specification and initial repository setup only.** There is no simulator, runnable application, animation, installed dependency set, or evaluation result yet. Implementation and paid model runs require a later go-ahead.

## Specification

[SPEC.md](SPEC.md) preserves the approved specification, version 1, unchanged. Its sentence saying nothing is published yet records the design-stage status when it was written; publication of this repository has since been authorized. The planned implementation remains unstarted.

The spec's PFAI lecture references are attribution by title and PDF page only. The repair world and procedural repair checklists are original adaptations; private course slides, PDFs, notes, and links are not distributed here. No open-source license has been selected or granted by this setup.

## Local configuration for future implementation

No API key is needed to read or review this repository. An ignored local `.env` can hold future configuration; `.env.example` is the tracked blank template. On a fresh clone, copy the template to `.env` only if `.env` does not already exist.

Put your own key in the repository-root `.env` as `OPENAI_API_KEY=YOUR_KEY_HERE`. Never commit a real key, paste it into chat, or expose it in the UI or logs. The initial local `.env` contains blank values only. This repository currently has no code that reads it or makes API calls.

Leave `OPENAI_MODEL` blank until the exact Luna-family OpenAI API identifier is officially available, verified, and selected. Internal assistant model labels are not API identifiers. Pin the same selected model and decoding configuration across all three conditions at implementation time; do not silently substitute models.

## Planned build order

1. Deterministic simulator and auditable text traces; establish feasible fixed limits.
2. Three isolated memory policies and comparison reporting, including unfinished jobs and memory-maintenance tokens.
3. Gradio bays and event-driven animation replaying actual outcomes.

These are future milestones, not completed features. Dependency versions, execution commands, tests, and model availability must be verified when implementation begins.

## Official documentation checked

Checked **2026-10-28 (UTC)** against the current official documentation, rather than older tutorials. No package version or runtime compatibility has been tested in this documentation-only setup.

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
