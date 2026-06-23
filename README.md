# Workflow vs Agent — Customer Inquiry Demo

Side-by-side comparison of a **scripted-LLM workflow** (`workflow.py`) and an
**agent** (`agent.py`) handling the same customer inquiries with the same tools.

Both run on **claude-haiku-4-5**; the only variable is control flow.

## Quick start

### Browser UI (recommended for presentations)

```bash
pip install -r requirements.txt
cp .env.example .env          # add your ANTHROPIC_API_KEY
python app.py                 # open http://localhost:8080
```

Pick a scenario with the buttons at the top, or type your own inquiry.
Results stream live into two side-by-side panels — Workflow on the left,
Agent on the right — with every tool call shown as it happens.

### CLI (terminal / projector)

```bash
python run.py simple          # parity case
python run.py compound        # the kill shot
python run.py novel           # no matching template
python run.py --live          # type your own inquiry
```

## What to watch for

| Scenario | Workflow | Agent |
|----------|----------|-------|
| `simple` | One tool call, correct answer | One tool call, same answer — parity |
| `compound` | Correctly says "address change impossible" — **then stops** | Follows the "if not X then Y" conditional — cancel + refund |
| `novel` | Generic fallback (no matching template) | Looks up damage policy, proposes resolution, escalates |

The key visual on `compound` is the **tool call sequence**. The workflow shows
one tool call and one reply. The agent shows multiple tool calls and a reply that
addresses the whole inquiry. That difference in the call trace *is* the lesson.

## The honest trade-off

Agents are not free:
- **Non-determinism** — the agent may choose a different tool order on repeat runs.
- **Latency** — multiple sequential model+tool round-trips vs. the workflow's one call.
- **Cost** — more tokens and calls on every request.
- **Confidently wrong** — the agent can fabricate eligibility. The `[ESCALATE]`
  flag exists precisely because adaptability and hallucination are the same
  capability viewed from two sides.

**The grown-up architecture:** hybrid routing. A cheap classifier sends the easy
80% to templated workflows and routes only compound/novel cases to the agent. You
get determinism where it's safe, adaptability only where you're paying for a reason.

## File layout

```
data/            local JSON + policy text (no real customer data)
tools.py         shared tool functions (both runners import from here)
scenarios.py     the three demo inquiries
workflow.py      scripted-LLM pipeline
agent.py         ReAct tool-use loop
run.py           CLI: python run.py <scenario>
app.py           Flask web server (http://localhost:8080)
static/
  index.html     browser UI — scenario buttons + streaming side-by-side panels
```
