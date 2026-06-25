# What `workflow.py` Does — Step by Step

## Entry point: `run_workflow(inquiry, notify=None)`

Sets up an `emit()` helper (prints to terminal in CLI mode, or streams SSE events in web mode), creates the Anthropic client, then runs two phases.

---

## Phase 1 — Classify (`_classify`)

One LLM call. The model receives the raw inquiry and a strict system prompt listing 6 valid intent labels. It must reply with **only the label name** — no explanation. Temperature 0, max_tokens 20.

```
shipping_status | address_change | cancel_refund | damage | returns | other
```

If the inquiry has two intents (e.g. "change address, and if not possible, cancel it"), the classifier is told to pick only the **primary** intent and ignore the conditional fallback. This is where the structural weakness is deliberately planted.

---

## Phase 2 — Route + execute template (`_run_template`)

The intent label is used to look up a pre-written system prompt in `_TEMPLATE_SYSTEMS`. Each prompt is focused on exactly one intent and instructs the model which tool to call:

| Intent | Tool called |
|---|---|
| `shipping_status` | `get_shipping_status` |
| `address_change` | `get_shipping_status` |
| `cancel_refund` | `lookup_policy('cancellation')` |
| `damage` | `lookup_policy('damage')` |
| `returns` | `lookup_policy('returns')` |
| `other` | *(no LLM call — generic fallback text only)* |

`_run_template` makes at most **two more LLM calls**:
1. LLM call with the intent-specific system prompt → model either responds with text (done) or requests a tool call.
2. If tool call: execute it, feed the result back → second LLM call produces the final reply.

The template runner handles **exactly one tool call** — there is no loop.

---

## Total call budget

```
run_workflow(inquiry)
  ├── LLM call #1  →  intent label         (classify)
  ├── dict lookup  →  system prompt        (routing)
  ├── LLM call #2  →  tool_use or text     (template, r1)
  │     └── if tool_use:
  │           execute_tool(name, input)
  │           LLM call #3  →  final reply  (template, r2)
  └── emit("reply", text)
```

**2–3 LLM calls total. 0 or 1 tool calls. No loops, no re-evaluation.**

---

## Why it breaks on the compound scenario

The classify step commits to one intent up front. After that, the template only resolves that one intent and returns. There is no mechanism to check the result of the first intent and then pursue the fallback — that decision point was never written into the flowchart.
