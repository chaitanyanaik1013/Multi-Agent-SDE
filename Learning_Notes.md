# Multi-Agent SDE — Learning Notes

A running reference of concepts covered while building this project, in the order they came up. This file gets added to as we go — treat it as your own notes, not a spec.

---

## 1. Project scope

- **What it does today, and what it will do:** the pipeline (PM → Architect → Backend → QA → ...) produces **planning artifacts** — a requirements doc, an architecture description, an API/backend spec, a test plan — not actual runnable application code. This matches the system-design doc's own "What the User Gets" file list (`requirements.md`, `architecture.md`, `schema.sql`, `openapi.yaml`, etc.) — it's a **planning/spec-generation system**, meant to hand a complete package to a human dev team (or to yourself) to build from.
- **Real code generation is a deliberate future phase**, not abandoned. The project is named "Software Development Engine" because the actual end goal is a working product. Adding a tool-using "Developer/Coder agent" later (one that can write files, run commands, not just return text) is architecturally compatible with everything built so far — no redesign needed. See the reasoning under "Future phases" below.
- **Public deployment (portfolio use) needs abuse/cost protection** — rate limiting, a hard spend ceiling, and cached demo results by default — planned for the deployment phase (step 5/6), not built yet.

---

## 2. The shared state ("notebook") pattern

Every agent is a plain function: `def run_x_agent(state: dict) -> dict`. Nothing is passed directly between agents — they only communicate by reading and writing fields on a shared `state` dict, which flows through the whole pipeline like a notebook being handed from one person to the next.

**Why agents return a *new* dict (`{**state, ...}`) instead of mutating `state` directly:**
- Not a bug-fix today (single agent, single process) — mutating in place would actually work fine right now.
- It matters once agents run as **separate processes** (e.g. Celery workers) with no shared memory — at that point, returning a full copy isn't a style choice, it's the only way to communicate at all.
- It matches LangGraph's own convention: nodes return updates, they don't mutate the input.
- It avoids collisions when **parallel** agents (Backend/Frontend/QA later) all start from the same notebook at once — each makes its own copy, and a "join" step merges them back together afterward (see section 8).

**The `**state` spread gotcha:** writing the same dict key twice in one dict literal doesn't merge — the second occurrence completely replaces the first. That's why `metrics` is built with its *own* nested spread:
```python
"metrics": {
    **state.get("metrics", {}),   # preserve other agents' existing entries
    "pm_agent": {...}             # add/overwrite only this agent's entry
}
```
Without the inner spread, each agent's metrics write would silently erase every other agent's metrics.

---

## 3. Calling the Claude API (Anthropic SDK)

**Client setup:**
```python
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()          # reads .env into environment variables
client = Anthropic()   # auto-picks up ANTHROPIC_API_KEY from the environment
```

**One API call:**
```python
response = client.messages.create(
    model="claude-haiku-4-5",   # cheapest current model — used for all agents during testing
    max_tokens=2048,             # hard cap on response length only, not on cost of input history
    system=system_prompt,        # the agent's "job description" — stable across calls
    messages=[
        {"role": "user", "content": user_prompt}   # the specific task for this call
    ]
)
```
- `messages` is always a **list** because the API models a conversation transcript, even for one-shot calls.
- `client.messages.create` is a **method** — `create` is a function belonging to the `messages` sub-object of `client`.
- The API is **stateless** — it has no memory between calls. Multi-turn conversations work by manually appending each new turn (`{"role": "assistant", ...}`, then the next `{"role": "user", ...}`) and resending the whole growing list every time.

**Reading the response:**
```python
response.content[0].text
```
`response.content` is a list because a reply can contain multiple kinds of blocks (text, tool calls, thinking) — we only ever have one plain text block, so `[0].text` gets it.

**Token cost control (for later, not needed yet):**
- `max_tokens` only caps the *response*, not the cost of resending a growing conversation history.
- Real levers: trimming/summarizing old turns, and prompt caching (Anthropic charges ~10% price for content it's recently already processed).
- Not relevant to any agent built so far — each one is a single-shot call, no growing history.

---

## 4. Tracking metrics (tokens, cost, latency)

```python
start = time.time()                          # set right before the API call
response = client.messages.create(...)
tokens_in = response.usage.input_tokens
tokens_out = response.usage.output_tokens
cost_usd = (tokens_in/1_000_000)*1.00 + (tokens_out/1_000_000)*5.00   # Haiku 4.5 pricing: $1/$5 per million
latency = time.time() - start                # measures only the API call itself
```
`start = time.time()` must be **inside** the function (reset every call), not at module level (would only be set once, when the file first loads).

---

## 5. Python imports/packaging (the gotchas we actually hit)

- Running a file directly (`python path/to/file.py`) only adds *that file's own folder* to Python's search path — nothing above it.
- `__init__.py` (empty files) mark a folder as a proper importable package. Added to `multi_agent_sde/` and `multi_agent_sde/agents/`.
- Absolute imports (`from multi_agent_sde.shared_client import client`) always resolve starting from wherever `multi_agent_sde` itself is discoverable — regardless of how deep the *importing* file is nested. This is why both `pm_agent.py` and `architect_agent.py` (at different folder depths) can use the exact same import line.
- Run scripts as modules from the **repo root**: `python -m multi_agent_sde.agents.pm_agent` or `python -m multi_agent_sde.main` — not `python multi_agent_sde/agents/pm_agent.py` directly.
- `shared_client.py` lives inside `multi_agent_sde/` (not the repo root) — kept there deliberately since the repo root shouldn't accumulate app code until there's a real backend/production setup.

---

## 6. Agents built so far

All four use the identical shape: build a system/user prompt from `state`, call Claude (`claude-haiku-4-5`, `max_tokens=2048`), extract the text, track metrics, return `{**state, "<field>": ..., "metrics": {...}}`.

| Agent | Reads from state | Writes to state | Metrics key |
|---|---|---|---|
| PM (`pm_agent.py`) | `user_input` | `requirements` | `pm_agent` |
| Architect (`architect_agent.py`) | `requirements` | `architecture` | `architect_agent` |
| Backend (`backend_agent.py`) | `architecture` | `backend_spec` | `backend_agent` |
| QA (`qa_agent.py`) | `requirements`, `architecture`, `backend_spec` | `test_plan` | `qa_agent` |

**Design decision made twice (Architect, then Backend):** each agent's Claude reply is one blob of text; rather than parsing it into multiple state fields (e.g. splitting `architecture` from `db_schema`), we keep it as a single field for now. Simpler, matches PM's shape, can split later if actually needed.

---

## 7. Manual pipeline (`main.py`, before LangGraph)

```python
state = {"project_id": "test-1", "user_input": "..."}
state = run_pm_agent(state)
state = run_architect_agent(state)
state = run_backend_agent(state)
state = run_qa_agent(state)
```
Each call overwrites `state` with the new notebook the previous agent handed back — the literal "notebook passed down the chain" pattern in action, run by hand before any framework is involved.

---

## 8. Sequential vs. parallel notebooks

- **Sequential** (what's built so far): every step produces one new full copy of the notebook; from a distance it looks like one notebook "growing," even though a fresh dict is technically created at each step.
- **Parallel** (planned for later — Backend/Frontend/QA fanning out simultaneously): all three start from the *same* notebook, but each produces its *own* separate copy with only its own new field added. A "join" step then merges the three separate copies back into one combined notebook before the next stage (Reviewer) runs. Doing this by hand means manually picking each agent's new field out of its own copy; once LangGraph is driving this, it merges parallel branches automatically.
- **Why copies matter more than it seems today:** in the real system, Backend/Frontend/QA will run as separate Celery worker processes — literally no shared memory at all. Returning a new notebook isn't a style choice at that point, it's the only way independent processes can ever combine results.

---

## 9. LangGraph basics (step 2 of the build plan)

```python
from langgraph.graph import StateGraph, END
from multi_agent_sde.state import WorkflowState

builder = StateGraph(WorkflowState)                       # a blank flowchart, typed to WorkflowState

builder.add_node("pm_agent", run_pm_agent)                # register each agent as a labeled box
builder.add_node("architect_agent", run_architect_agent)
builder.add_node("backend_agent", run_backend_agent)
builder.add_node("qa_agent", run_qa_agent)

builder.set_entry_point("pm_agent")                       # where execution starts
builder.add_edge("pm_agent", "architect_agent")           # arrows connecting the boxes in order
builder.add_edge("architect_agent", "backend_agent")
builder.add_edge("backend_agent", "qa_agent")
builder.add_edge("qa_agent", END)                         # END = built-in "graph is done" marker

workflow = builder.compile()                              # finalize the blueprint into a runnable graph
result = workflow.invoke(state)                           # actually run it, starting from `state`
```

- `StateGraph(WorkflowState)` needs `WorkflowState` (the `TypedDict` in `state.py`) kept in sync with every field agents actually read/write — updated to include `architecture`, `backend_spec`, `test_plan` when we got here.
- `add_node` takes a **name** (a string label used for wiring edges) and the **function itself** (not called — no `()`).
- `builder` = "graph under construction"; `workflow` (after `.compile()`) = the actual runnable thing.
- **Fixed edges vs. conditional edges:** everything here uses fixed edges (`add_edge`) — the order is hardcoded by us, not decided by an LLM. LangGraph *also* supports **conditional edges** (`add_conditional_edges(node, router_function)`), where a plain Python function you write decides what runs next — and that function is free to call an LLM internally to make the decision. That's a different, valid pattern (used in a past interview-agent project), but not what this project's design uses — this pipeline's order is fixed by design.
- **LangGraph vs. LangChain:** LangChain is built for simple, mostly-linear chains. LangGraph is built for stateful, graph-shaped workflows — specifically because this project needs things a plain chain can't do: **pausing and resuming** (approval gates, step 3) and **parallel branching with merging** (step 4). Today's 4-agent fixed sequence doesn't strictly need either framework — the payoff shows up once gates and parallel execution are added.

**Where the input will actually come from later:** right now `state = {"project_id": "test-1", ...}` is hand-typed. In production (step 5), a real `POST /projects` API request supplies this instead — FastAPI builds the actual `WorkflowState` from the request body and hands it to `workflow.invoke(...)`, usually inside a Celery background task. The hardcoded test dict is a stand-in for that, appropriate for this stage.

---

## 10. Build sequence roadmap (for orientation)

1. **Plain Python agent functions, no LangGraph** — ✅ done (PM, Architect, Backend, QA; manual chaining in `main.py`).
2. **Wire the same functions into LangGraph** — in progress (graph built; not yet run with a real API key).
3. **Approval gates** via `interrupt_before` + a Postgres checkpointer — not started.
4. **Parallel fan-out** with `Send()` (Backend/Frontend/QA simultaneously) — not started.
5. **FastAPI + Celery** for real async background jobs, and the real `POST /projects` entry point — not started.
6. **Observability, eval suite, memory layer, deployment (with abuse protection)** — not started.

Future, deferred scope: an actual code-writing Developer/Coder agent (tool-use based), added after the above, per the "SDE" end-goal discussion.
