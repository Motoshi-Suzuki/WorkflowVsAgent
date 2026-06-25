# What `agent.py` Does — Step by Step

## Entry point: `run_agent(inquiry, notify=None)`

Sets up the same `emit()` helper pattern as `workflow.py` (CLI prints or SSE events), creates the Anthropic client, and builds the initial message list:

```python
msgs = [{"role": "user", "content": inquiry}]
```

Then enters the tool-use loop.

---

## The loop: up to `MAX_ITERATIONS = 6` iterations

Each iteration makes one LLM call with the full conversation history so far (`msgs`), the agent system prompt, and the full `TOOL_DEFINITIONS` list. The model decides what to do next.

### Iteration outcome A — `stop_reason == "end_turn"`

The model produced a plain-text final answer. `emit("reply", text)` and return. Done.

### Iteration outcome B — `stop_reason == "tool_use"`

The model wants to call one or more tools. For **each** tool call block in the response:

1. `emit("tool_call", ...)` — prints the call to the terminal.
2. `T.execute_tool(name, input)` — runs the actual function from `tools.py`.
3. `emit("tool_result", ...)` — prints the result.
4. Appends the result to a `tool_results` list.

After all tool calls are processed, **both** the assistant's response and all tool results are appended to `msgs`:

```
msgs → [..., assistant_turn, tool_results_turn]
```

The loop then continues to the next iteration with the enriched history.

### Iteration outcome C — any other `stop_reason`

Unexpected. Emits a warning and returns whatever text is in the response.

---

## Cap handling: after 6 iterations

If the loop exhausts all iterations without an `end_turn`, one final LLM call is made with an amended system prompt:

> "You have used all 6 tool calls. Provide your best answer now based on what you have gathered."

This forces a text reply from whatever facts have been collected so far.

---

## Total call budget

```
run_agent(inquiry)
  └── for i in range(6):
        LLM call  →  end_turn  →  emit reply, return
                  →  tool_use  →  execute each tool
                                  append results to msgs
                                  continue loop
        (unexpected stop_reason)  →  warn + return

  if loop exhausted:
        LLM call (forced final)  →  emit reply
```

**1–7 LLM calls total. 0–6 tool calls. The model decides both which tools to call and in what order.**

---

## What makes it structurally different from the workflow

| | Workflow | Agent |
|---|---|---|
| Who writes the execution path? | The author (fixed routes) | The model (at runtime) |
| Classification step? | Yes — commits to one intent | No — model reads the full inquiry each time |
| Tool calls | At most 1, pre-determined by template | Up to 6, model-chosen |
| Conditional fallback handling | Dropped by classifier | Model evaluates condition, pursues fallback if needed |
| Re-evaluation after tool result | Never | Every iteration |
| Escalation | Not built in | System prompt instructs model to end with `[ESCALATE]` on policy edges |

---

## Why it handles the compound scenario

The agent never classifies. It reads the full inquiry — including the conditional ("if not possible, do Y") — on every iteration. After calling `get_shipping_status` and finding `can_change_address: false`, the model still has the original inquiry in context and reasons: "address change is not possible → I should now pursue the cancel+refund path." It then calls `lookup_policy('cancellation')` on the next iteration and produces a complete reply covering both parts.
