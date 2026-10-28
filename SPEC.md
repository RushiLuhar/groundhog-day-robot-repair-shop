# Groundhog Day Robot Repair Shop

## The idea in plain English

Three copies of **Sprocket, the mechanic**, work in three neighboring repair bays. Broken robot customers arrive in the same order, with identical faults. Sprocket inspects each customer, chooses repairs, and tests whether they worked. We compare the same AI with three memory settings—not three different models.

At every new job, Sprocket starts a fresh conversation. One copy forgets previous jobs; one carries its last 12 turns; one keeps organized working, episodic, semantic, and procedural memory. Its model weights never change. “Learning” means using experience saved outside the model.

For example, an Amber R1 customer needs **vent → tune → seal**. Tuning first fails. On a repeat job, can Sprocket avoid that mistake? If the next customer is already vented, can it skip that step? If a visibly different revision arrives, can it check rather than blindly reuse yesterday’s recipe?

We count **steps needed to finish each job** and **tokens spent**. Tokens are this garage’s fictional cash: Sprocket presents the actual token bill. At the step cap, it drops the wrench and takes a smoke break. Three pixel-art animations show real outcomes, including unfinished jobs—not a scripted memory-system victory.

This is a design specification only. Nothing is being implemented or published yet.

## A small repair world

A deterministic Python simulator represents two fictional families, Amber and Mint, with three components: cooler, cable, and fuse. Repairs are vent, tune, seal, reseat cable, and replace fuse. These are invented rules, not real engineering.

The agent has three tools:

- **inspect:** reveal model, revision, diagnostic readings, and visible repair progress—not the hidden repair recipe.
- **operate:** attempt one named repair; return the observed result. Wrong-order operations leave state unchanged and consume a step.
- **test:** run the customer and return pass or an observable failure report. Only a passing test completes a job.

“Stuttering” can have different causes. The mechanic must diagnose, respect dependencies, account for work already done, and sometimes fix two faults. Feedback exposes local constraints, not the entire solution. Every job must be discoverable without previous memory: remembering should save work, not unlock an impossible puzzle.

## The ten jobs

The following order and a versioned seed are fixed before evaluation. Each bay gets a separate, identical customer state. Solution notes explain the experiment; they are **not** included in the agent’s job ticket.

| Job | Customer and starting problem | What the job tests |
| --- | --- | --- |
| 1 | Amber R1, stuttering from a cooler fault | Discover vent → tune → seal. |
| 2 | Mint R1, apparently similar cooler fault | Discover its different order: tune → vent → seal. |
| 3 | Amber R1, same starting fault as job 1 | Exact repeat: avoid rediscovery. |
| 4 | Amber R1, cooler already vented | Transfer: inspect, then perform only missing work. |
| 5 | Mint R1, stuttering from a loose cable | One-off diagnosis: reseat the cable, not the cooler. |
| 6 | Mint R1, no startup because of a blown fuse | One-off repair: identify and replace the fuse. |
| 7 | Amber R1, cooler fault **and** loose cable | Combine repairs; one familiar recipe is insufficient. |
| 8 | Mint R1, same starting fault as job 2 | Delayed repeat after unrelated jobs. |
| 9 | Amber **R2**, cooler fault | Notice the revision; its order is now tune → vent → seal. |
| 10 | Amber R2, cooler already tuned | Apply the revised lesson without repeating finished work. |

The revised label is visible, but the new recipe must be learned from tools. The simulator preserves family rules between jobs; the customer and conversation reset. A new experimental run resets **all** memory.

## Exactly three memory settings

All three use the same pinned **OpenAI Luna-family model**, decoding settings, instructions, tools, and current-job transcript. Propose a **12-tool-call cap per job**, checked for feasibility before freezing it for all modes. Every tool call—including inspection and testing—is one step; allow one call per turn. A non-action response ends the job unfinished.

1. **Groundhog Day — no persistent memory.** Keep the current job’s working state; discard everything at the next customer.
2. **Raw notebook — last 12 turns.** Carry the latest 12 complete action/result exchanges from earlier jobs, verbatim and chronologically. One turn includes the assistant’s action and its full tool response; attach its original job ticket and boundary labels. No summaries, extracted lessons, selective retrieval, or dropped tool results. Keep this prior-history window fixed during the current job; rebuild it at the next boundary. Current-job history is separate and available in full to every setting.
3. **Four-level memory.** Keep current-job working state plus three compact, persistent stores described below. Cap the combined stored notes at 1,000 tokens and load them in full; this tiny world does not need embeddings or a vector database.

This compares memory policies, **not equal token budgets**. Do not trim raw history to match compressed notes. Match repair-time generation limits and tool budgets; count the structured mode’s additional memory-maintenance call. No mode sees hidden simulator state, another bay’s experience, or future jobs.

## What the four levels contain

Use PFAI’s **Lecture 4 - Slides.pdf** as the primary source: working memory pp. 52–54, episodic pp. 55–57, semantic pp. 58–60, procedural pp. 61–67, and memory lifecycle p. 68. Page numbers refer to the PDF.

| Memory | Plain meaning | Concrete example |
| --- | --- | --- |
| **Working** | What matters for this job, now | “Amber R1; vent completed; tune and seal remain; 8 steps left.” |
| **Episodic** | What happened on a particular job | “Job 1: tuning failed before venting; vent/tune/seal subsequently passed.” |
| **Semantic** | A supported fact that may apply again | “Amber R1 requires venting before tuning.” |
| **Procedural** | A reusable way to do the work | “For an unmodified Amber R1 cooler: inspect progress, vent if needed, tune, seal, test.” |

Display four levels, but implement cooperating types—not compulsory promotions through four stages. Persistent notes feed working context. **Repair checklists adapt** the course’s procedural examples, which focus on preferences and habits; they are not an example copied from the slides. Direct notes without vector search follow p. 69.

After each job, one bounded call to the same model updates notes from observed results, recording model/revision, source job IDs, and tentative versus test-supported lessons. Failures remain episodes, not successful procedures. R2 does not overwrite R1; contradictions mark the applicable note disputed. Validation checks structure and references, not a hidden answer key.

## Straightforward LangGraph structure

Use one `StateGraph`: **load memory → decide → execute tool → decide again → finish → save memory**. Conditional edges stop on completion or the limit. Messages and current-job fields live in graph state, using the official [Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api) and [tool-loop quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart).

Use `InMemorySaver` with fresh mode/run/job thread IDs and `InMemoryStore` for permitted cross-job records, in isolated namespaces. These documented [memory primitives](https://docs.langchain.com/oss/python/langgraph/add-memory) suffice in-process. Keep scoring/replay logs inaccessible to agents. No vector database, multi-agent judge, or fine-tuning.

Verify Luna’s exact API identifier at implementation time. Configure the key as a server-side secret, never in the UI or logs. No key or paid runs are needed for this specification.

## The Gradio shop window

Use [Gradio Blocks](https://gradio.app/docs/gradio/blocks) for three bays, each showing memory setting, job, steps, token till, and pass/unfinished. Below: an event timeline and memory drawers showing exactly what the mechanic could read and what changed.

Art direction: a disreputable 1980s anime garage in chunky pixels—greasy overalls, dangling cigarettes, flickering neon, CRT diagnostics, terrible jokes. Sprocket mutters “Same shit, different serial number.” Broken customers look distinct from their mechanics.

An [HTML component](https://gradio.app/docs/gradio/html) renders pixel-style SVG/CSS animation; [generator updates](https://gradio.app/guides/streaming-outputs) advance logged events. Inspecting raises a scanner; repairs move tools; rejection causes a splutter; only a passing test triggers celebration. At the cap, Sprocket abandons the job for cigarettes and coffee. Banter and animation use no additional model calls or diagnostic information.

The till counts actual API-reported input and output tokens across **all** calls, including memory maintenance. After accounting settles: “That’ll be X tokens, pal.” This is fictional currency, not dollars or a real payment. Animation delays do not affect scoring.

## Comparison and minimum scope

Run the shift three times per setting, starting with empty memory. Show every job’s **steps to successful completion** and **total tokens**, with input/output and maintenance subtotals. Mark failures “unfinished after X/12 steps,” never efficient completions. Show completions alongside step averages so early quitters cannot win. No result is predetermined.

Build only after approval: **first** the simulator and auditable text traces; **then** the three memory policies and comparison table; **finally** Gradio and event-driven animation. Verify identical starting states, isolation between modes, and faithful replay before treating the demo as evidence.
