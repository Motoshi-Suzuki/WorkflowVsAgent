# SPEC.md — Build & Demo Reference

This is the detailed companion to `CLAUDE.md`. It pins down the data, the exact
scenarios, the behaviour each system should exhibit, and the talking points so
the demo *lands* and survives a sharp question.

---

## 1. Data (`data/`)

Keep it tiny — three orders is enough.

**orders.json**
| id   | customer_id | items            | status     | order_date | total |
|------|-------------|------------------|------------|------------|-------|
| 1001 | C1          | 1x Desk Lamp     | shipped    | day -3     | 4,200 |
| 1002 | C2          | 1x Office Chair  | shipped    | day -1     | 28,000|
| 1003 | C3          | 1x Coffee Beans  | delivered  | day -6     | 1,800 |

**shipping.json**
| order_id | state      | dispatched_at | eta     | can_change_address |
|----------|------------|---------------|---------|--------------------|
| 1001     | in_transit | day -2        | day +1  | false              |
| 1002     | dispatched | day -1 (12h ago)| day +2| **false**          |
| 1003     | delivered  | day -5        | —       | false              |

**customers.json**: C1/C2/C3 with name, email, tier (standard/standard/premium).

**policies.md** — short prose blocks the agent can `lookup_policy` against:
- **address_change**: allowed only while state == `processing`. Once
  dispatched, not possible.
- **cancellation**: allowed before delivery; if already dispatched, customer
  must refuse delivery or return after receipt.
- **refund**: full refund within 30 days of delivery for unopened items;
  dispatched-but-undelivered orders can be refunded on return-to-sender.
- **damage**: damaged/mishandled deliveries → replacement or full refund,
  always routed to a human for goodwill assessment.
- **returns**: 30-day window, prepaid label.

The key rigged fact: **order 1002 is already dispatched**, so a date/address
change is *impossible* by policy. This is what the compound scenario hinges on.

---

## 2. The three scenarios (`scenarios.py`)

### `simple` — proves the workflow is competent (parity case)
> "Hi, where's my order 1001? When will it arrive?"

- **Workflow**: classify → `shipping_status` → `get_shipping_status(1001)` →
  template → "In transit, ETA tomorrow." Correct.
- **Agent**: one tool call, same answer.
- **Audience takeaway**: for bounded, single-intent work, the workflow is fine —
  and cheaper/faster. Do NOT skip this scenario; it's what makes you credible.

### `compound` — the kill shot (conditional across two intents)
> "Can you change the delivery on order 1002 to tomorrow? If that's not
> possible, just cancel it and refund me."

- **Workflow**: classifies ONE intent (e.g. `address_change`). Even a *good*
  template here correctly checks shipping, sees `can_change_address == false`,
  and replies "Sorry, 1002 has already been dispatched, so we can't change the
  delivery date." **Then it stops.** It never touches the refund fallback,
  because that second, conditional intent was never classified. It is *correct
  on the half it handled and silent on the half that mattered.*
- **Agent**: `get_shipping_status(1002)` → dispatched → change impossible →
  *therefore* pivots to the fallback → `lookup_policy(cancellation)` +
  `lookup_policy(refund)` → `get_order(1002)` for eligibility → composes one
  reply: "Date change isn't possible (already dispatched); per policy I've
  started the cancellation/return-to-sender refund path; [flag: confirm refund
  with a human]."
- **Why it survives scrutiny**: the failure is the "if not X then Y" dependency
  across two intents. You genuinely cannot draw that on a flowchart in advance
  without enumerating every conditional pair a customer might write. That
  non-enumerability *is* the workflow's structural ceiling.

### `novel` — no matching intent
> "Your driver left my parcel out in the rain and the box is soaked. What are
> you going to do about it?"

- **Workflow**: matches no clean order-status/refund/address intent → generic
  fallback: "Thanks, a representative will get back to you." Dead end.
- **Agent**: `lookup_policy(damage)` → reasons it's a goodwill/replacement case →
  `get_order` to identify the item → proposes replacement or refund → **flags
  for human** per the damage policy. Reasons about a case nobody templated.

---

## 3. Expected on-screen contrast (what to point at)

The visible difference MUST be architectural, not prose quality. On the
`compound` run the audience should see:

```
--- WORKFLOW ---
[classify] intent = address_change
[tool] get_shipping_status(1002) -> dispatched
[reply] "We can't change the date, 1002 has already been dispatched."
        (no mention of the cancel/refund request)

--- AGENT ---
[tool] get_shipping_status(1002) -> dispatched, can_change_address=false
[tool] lookup_policy(cancellation) -> ...
[tool] lookup_policy(refund) -> ...
[tool] get_order(1002) -> ...
[reply] "Date change isn't possible — already dispatched. Per our policy I've
         started the return-to-sender refund. A teammate will confirm the
         refund amount. [ESCALATE]"
```

One line workflow, four lines agent: *the model wrote that sequence at runtime.*
That picture is the lesson. If you only show the two final paragraphs, the room
sees "nicer wording" and misses the point — so **print the tool calls.**

---

## 4. The honest trade-off slide (do not skip — it's what earns trust)

Agents are not free. State this plainly to an engineering-literate room:

- **Non-determinism**: the agent may choose a different tool order on different
  runs. Show it. Workflows are reproducible; agents are not.
- **Latency**: several sequential model+tool round-trips vs. the workflow's one
  call. Visible on stage.
- **Cost**: more tokens, more calls, every time.
- **Confidently wrong**: the agent can fabricate a policy or invent eligibility.
  This is why the escalation flag exists. Adaptability and hallucination are the
  *same* capability viewed from two sides.

**The grown-up architecture (your closer):** hybrid routing. A cheap classifier
sends the easy, high-volume 80% to templated workflows and routes only the
compound/novel long tail to the agent. You get the workflow's determinism and
cost where it's safe, and the agent's adaptability only where you're paying for
a reason. "Agent or workflow" is a false binary; the real answer is *which, for
which inquiry.*

---

## 5. Model / config notes
- Default model `claude-sonnet-4-6`, same on both sides, temperature 0.
- Agent loop cap: ~6 iterations (prevents an infinite tool loop — itself a
  named agent failure mode worth a one-liner on stage).
- If you'd rather demo in Node: the architecture is unchanged — swap the SDK and
  keep `tools.py`'s contract identical across both runners.

---

## 6. Live mode (v2, optional, high payoff)
`python run.py --live` accepts a typed inquiry. Invite the room to throw a
curveball at the agent. Keep a known-good compound inquiry as a backup in case
the network or the model misbehaves, and have a recorded run ready. A live
mis-recovery is not a failure of your demo — it *is* the "confidently wrong"
lesson, delivered for free.
