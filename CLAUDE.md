# CLAUDE.md — Customer Inquiry Demo (Agent vs. Scripted-LLM Workflow)

## What we are building
A small, local, side-by-side demo for a presentation. It takes a single
customer inquiry and runs it through **two systems** that share the same tools
and the same data:

1. `workflow.py` — a **scripted LLM workflow**: one classification call, then a
   fixed template path the *author* wrote.
2. `agent.py` — an **agent**: a tool-use loop where the *model* decides which
   tools to call and in what order.

The point of the demo is to show, on screen, that the workflow handles the easy
cases but breaks on the unanticipated ones, while the agent adapts — and to be
honest about what that adaptability costs.

## The single most important rule
**Do not strawman the workflow.** It must be a *competent* implementation: a
good classifier, well-written templates, and it may even call a tool. It should
fail on the hard scenario because of its **architecture** (it commits to one
intent up front), not because we crippled it. If the workflow fails on something
a single extra `if` branch would fix, the demo is broken — a viewer will just
say "add the branch."

## Hard design constraints (these protect the thesis)
- **Both systems call the LLM.** The contrast is *agentic* vs. *scripted-LLM*,
  NOT LLM vs. no-LLM. Never let the workflow become a dumb regex.
- **Same model on both sides** (default `claude-sonnet-4-6`). The only variable
  we are demonstrating is control flow, so model capability must be held
  constant. Do not use a weaker model for the workflow.
- **Identical, shared tools.** Both runners import the exact same functions from
  `tools.py`. Neither side gets a tool the other lacks.
- **The agent's tool calls must be visible.** Print every tool call and its
  result to the terminal as it happens. The audience needs to *watch the model
  decide what to call next* — that is the entire teaching point (locus of
  control). The workflow should likewise print its one classification + path.
- **Deterministic data, low temperature.** All data is local JSON/markdown.
  Temperature 0 (or 0.2). The injected difficulty comes from the *scenario*, not
  from randomness.
- **No real customer data, no real network** except the Anthropic API. API key
  from `OPENAI`/`ANTHROPIC_API_KEY` env var via `.env`; never commit it.

## File layout
```
inquiry-demo/
  CLAUDE.md            # this file
  README.md            # how to run, what the audience should watch for
  .env.example         # ANTHROPIC_API_KEY=...
  requirements.txt     # anthropic, python-dotenv
  data/
    orders.json
    customers.json
    shipping.json
    policies.md
  tools.py             # shared fake tools (read from data/)
  workflow.py          # scripted-LLM pipeline
  agent.py             # tool-use loop
  scenarios.py         # the 3 demo inquiries
  run.py               # CLI: `python run.py <scenario>` runs BOTH, side by side
```

## Shared tools (`tools.py`)
All read from `data/`. Keep signatures identical for both runners.
- `get_order(order_id) -> dict` — items, status, order_date, customer_id, total
- `get_shipping_status(order_id) -> dict` — state in
  {processing, dispatched, in_transit, delivered}, dispatched_at, eta,
  `can_change_address: bool`
- `get_customer(customer_id) -> dict` — name, email, tier
- `lookup_policy(topic) -> str` — topic in {refund, address_change,
  cancellation, returns, damage}; returns the relevant policy text from
  `policies.md`

## How each system works
**Workflow (`workflow.py`)** — the author wrote this flowchart:
1. One LLM call: classify the inquiry into exactly ONE intent.
2. Route to the template for that intent. The template may make ONE tool call.
3. Fill the template and return. No re-evaluation, no second intent.

**Agent (`agent.py`)** — a ReAct-style loop:
1. System prompt lists the tools and the goal: "resolve the inquiry fully; if a
   policy edge is hit, flag for human escalation rather than inventing an answer."
2. Loop: model emits tool calls -> we execute -> feed results back -> repeat
   until it produces a final answer. Cap at ~6 iterations.
3. Print each tool call + result. Final answer addresses *every* part of the
   inquiry and includes an escalation flag where warranted.

## Run UX (`run.py`)
`python run.py compound` prints, clearly separated:
- the inquiry,
- `--- WORKFLOW ---` : its single classification, its one path, its reply,
- `--- AGENT ---` : each tool call/result in sequence, then its reply.
Keep it readable on a projector: short lines, clear section headers.

## Staged build
- **v0**: tools + data + the three scenarios + workflow only. Confirm the
  workflow answers the simple case well. (Proves it isn't a strawman.)
- **v1**: add the agent loop. Run all three side by side.
- **v2**: polish the on-screen formatting; add a `--live` mode that accepts a
  typed inquiry so the audience can throw their own curveball.

## Guardrails (demo hygiene)
- Draft/demo only: nothing sends email, charges, or mutates real systems.
- No credentials in the repo; `.env` is git-ignored, `.env.example` is committed.
- The agent must escalate (flag for human) on policy edges rather than fabricate
  eligibility — this is itself a talking point about agent failure modes.
