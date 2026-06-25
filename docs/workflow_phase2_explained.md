# Workflow Phase 2 Deep Dive — Tools & Template Execution

## What is a "tool" in this context?

A tool is a Python function in `tools.py` that the LLM is *allowed to call* — but cannot call directly. The flow is:

1. The LLM says "I want to call `get_order` with `order_id='1001'`" in its response (as a structured `tool_use` block, not free text).
2. **Your Python code** receives that request, calls the actual function, and feeds the result back to the LLM.

The LLM never touches `tools.py` directly. It just asks, and the runner decides whether and how to execute it.

---

## The 4 tools and what they actually do

All four read from local JSON/markdown files in `data/`. No network, no database.

### `get_order(order_id)` → `dict`
Reads `data/orders.json`. Returns the full order record for that ID:
```json
{ "id": "1001", "customer_id": "C1", "items": [...], "status": "dispatched", "order_date": "...", "total": 59.99 }
```
Returns `{"error": "Order '1001' not found"}` if missing.

### `get_shipping_status(order_id)` → `dict`
Reads `data/shipping.json`. Returns the shipping record:
```json
{ "order_id": "1001", "state": "in_transit", "dispatched_at": "...", "eta": "...", "can_change_address": false }
```
The `can_change_address` boolean is the critical field — the address_change template uses it to decide if a redirect is still possible.

### `get_customer(customer_id)` → `dict`
Reads `data/customers.json`. Returns:
```json
{ "id": "C1", "name": "Alice Smith", "email": "alice@example.com", "tier": "gold" }
```

### `lookup_policy(topic)` → `str`
Reads `data/policies.md` and parses it into sections by `## heading`. Valid topics: `refund`, `address_change`, `cancellation`, `returns`, `damage`. Returns the matching section as plain text so the LLM can reason about it and quote it in its reply.

---

## Phase 2 in detail: `_run_template`

The template system prompt (one per intent) already tells the model *which* tool to call. So in practice the first LLM call almost always returns a `tool_use` block. Here's the exact sequence:

### Step 2a — First LLM call (`r1`)

```
system:   intent-specific template prompt
user:     the original inquiry
tools:    all 4 TOOL_DEFINITIONS (model sees all, but prompt steers it to one)
```

The model responds with either:
- **Plain text** (rare) → return it immediately, done.
- **`tool_use` block** → extract it and proceed.

A `tool_use` block looks like:
```json
{ "type": "tool_use", "id": "toolu_abc", "name": "get_shipping_status", "input": {"order_id": "1002"} }
```

### Step 2b — Tool execution

```python
result = T.execute_tool(tool_block.name, tool_block.input)
```

`execute_tool` dispatches to the right Python function and serialises the result to a JSON string. The runner emits `"tool_call"` (what was asked) and `"tool_result"` (what came back) — this is what you see printed in the terminal.

### Step 2c — Second LLM call (`r2`)

The conversation is rebuilt:
```
system:   same template prompt
user:     original inquiry
assistant: [the tool_use block from r1]
user:     [tool_result block with the JSON string]
```

Now the model has the data it needed. It writes the final customer-facing reply. That text is returned and emitted as `"reply"`.

### The hard cap

`_run_template` has **no loop**. After step 2c it returns unconditionally. Even if the model wanted to call a second tool (e.g. also look up the customer's tier), it cannot — the runner just takes `r2`'s text and exits.

---

## Putting it together: what happens for the `address_change` template

1. System prompt tells model: "use `get_shipping_status`, check `can_change_address`."
2. First LLM call → `tool_use: get_shipping_status(order_id='1002')`
3. Runner calls `get_shipping_status('1002')` → returns `{"state": "dispatched", "can_change_address": false, ...}`
4. Second LLM call with that result → model writes: "Unfortunately your order has already been dispatched and the address can no longer be changed."
5. `emit("reply", ...)` → shown to user.

The model never sees the cancel/refund part of the inquiry, because the template prompt explicitly says *"Address ONLY the address-change request."* That is the structural constraint — not a bug, but the design.
