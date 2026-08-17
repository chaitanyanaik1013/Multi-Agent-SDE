# Multi-Agent SDE — Project Scope & Roadmap

A single reference for **what this project is, how far it goes, and where things currently stand.** Unlike `Learning_Notes.md` (which explains *concepts*), this file tracks *status and scope* — check here to answer "what's done, what's next, and does this feature belong in this project at all."

---

## Quick status snapshot

- **Currently on:** Step 2 (LangGraph wiring) — structurally complete, not yet run with a real API key.
- **Agents built:** 4 of 6 (PM, Architect, Backend, QA). Frontend and Reviewer remain — planned for Step 4.
- **Next up:** Step 3 — Approval gates.

---

## What this project actually is (and isn't, yet)

The project is named "Software Development Engine" because the **real end goal is a working product** — not just documentation. But the current, bounded scope of what's being built is a **planning/spec-generation pipeline**: six AI agents that turn a plain-English product idea into a complete package of planning artifacts (requirements doc, architecture description, API/backend spec, frontend spec, test plan, review report) — the same deliverables listed in the original system-design doc's "What the User Gets" section.

**Actual code generation (an agent that writes real, runnable source files) is explicitly out of scope for the current 6-step sequence** — it's a confirmed, deliberate future phase, added after this sequence completes. See "Deferred / future phases" below.

---

## The 6-step build sequence

This is the actual sequence being followed (agreed as a refinement of the original system-design doc's broader phases, split into smaller single-concept steps so async/LangGraph aren't learned tangled together).

### Step 1 — Plain Python agent functions, no LangGraph
**Status: ✅ Done.**
- Established the shared-state ("notebook") pattern: `def run_x_agent(state: dict) -> dict`, returning a new copy rather than mutating.
- Built 4 of the project's 6 agents: **PM, Architect, Backend, QA** — each one API call, one output field, metrics tracked (tokens, cost, latency).
- Manually chained all four in `main.py` (`state = run_pm_agent(state)`, etc.) — proved the notebook-passing pattern works across multiple real agents before any framework was introduced.
- Fixed along the way: Python packaging (`__init__.py`, absolute imports, running via `python -m`), a shared Anthropic client (`shared_client.py`).

### Step 2 — Wire the same functions into LangGraph
**Status: ✅ Structurally done — not yet run with a real key.**
- `WorkflowState` (TypedDict in `state.py`) brought up to date with all fields agents actually use.
- Built a `StateGraph`, registered all 4 agents via `add_node`, connected them in order via `set_entry_point` + `add_edge` + `END`, and ran it via `builder.compile()` → `workflow.invoke(state)`.
- Verified: running it reaches the real Claude API call inside the correct node (`pm_agent`) and fails only on the placeholder API key — confirming the graph mechanics are wired correctly.
- **Remaining for this step:** run it for real once a valid API key is added.

### Step 3 — Approval gates
**Status: ⬜ Not started. Next up.**
- `interrupt_before` + a PostgreSQL checkpointer — the graph pauses after a node runs (e.g. after PM, before Architect), saves full state to a real database, and can resume — potentially hours or days later — once a human approves.
- Called out in the original plan as the trickiest concept, deserving dedicated focus on its own.

### Step 4 — Parallel fan-out with `Send()`
**Status: ⬜ Not started.**
- Add the two remaining agents: **Frontend** and **Reviewer** (per the original system-design doc, these arrive alongside parallel execution, not in the initial core-4 phase).
- Backend, Frontend, and QA run **simultaneously**, each producing its own copy of the notebook from the same starting point; a "join" step merges the three copies back into one before Reviewer runs.
- This is where LangGraph actually performs the state-merging that would otherwise need to be done by hand (see `Learning_Notes.md` §8).

### Step 5 — FastAPI + Celery
**Status: ⬜ Not started.**
- Wraps the whole graph in a real web service: `POST /projects` accepts a real user's product idea, creates a project row in Postgres, and queues a Celery background task to actually run the graph — instead of the hand-typed `state = {...}` currently sitting in `main.py`.
- Deliberately placed after LangGraph/gates/parallel are solid, so async/background-job concepts (new to the user) are learned in isolation rather than tangled with graph concepts.
- **This is also where deployment abuse protection needs to be built** — see "Deferred / future phases" below.

### Step 6 — Observability, eval suite, memory layer, deployment
**Status: ⬜ Not started. Final step of the core sequence.**
- Metrics dashboard (per-agent cost/latency, already partially enabled by the `metrics` field every agent writes).
- A fixed benchmark suite (per the system-design doc: e.g. CRM, Expense Tracker, Blog) to measure quality/cost objectively across changes.
- ChromaDB memory layer (`past_decisions`, `user_preferences`) — deliberately last since the rest of the system works without it.
- Actual deployment (Docker Compose locally, Railway/Render for a public demo) — **must include the abuse-protection plan** (see below) before going publicly live.

---

## Deferred / future phases (beyond the 6-step sequence)

These are confirmed real goals, explicitly not part of the current sequence, and confirmed **architecturally compatible** with everything being built now — no redesign required when the time comes.

### A. Real code generation (the actual "SDE" payoff)
- A future Developer/Coder agent (or team of them) that uses **tool-use** (file-writing, running commands) to take the accumulated specs and produce an actual working codebase — not just descriptions of one.
- Requires two genuinely new things not covered anywhere in the 6-step sequence: (1) tool use / function calling with Claude, (2) a sandboxed code-execution/file-writing environment (e.g. a per-project workspace or container).
- Slots in as new nodes *after* the current planning pipeline — confirmed compatible with the shared-state pattern, LangGraph, gates, parallel execution, and the Celery async layer.

### B. Public deployment abuse protection
- Needed before the project goes live as a public portfolio piece, so bots/crawlers/general traffic can't trigger unlimited real (paid) API calls.
- Plan: rate limiting per visitor, a hard monthly spend ceiling (backed by the `metrics.cost_usd` tracking already built into every agent), cached demo results shown by default, and infra-level bot mitigation (CAPTCHA / hosting-platform filtering) for the one path that does trigger a real live call.
- Belongs in Step 5/6 (FastAPI + Celery, deployment) — not before.

---

## How this file is maintained

Updated whenever a build step's status changes (started, completed, or scope changes) — kept in sync with actual progress, not aspirational. Cross-reference `Learning_Notes.md` for how each concept actually works.
