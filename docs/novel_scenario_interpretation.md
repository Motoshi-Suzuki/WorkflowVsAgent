# Q&A: How to Interpret the "Novel" Scenario Results

## Question

> How should I interpret this result of novel?
>
> **Workflow — Scripted LLM**
> - intent = damage
> - `lookup_policy(topic='damage')`
> - Policy returned: full replacement or refund, must route to human agent, ask for order ID + photo, 1–2 business days
> - Reply: "Thank you for providing those details. Here's what we can do: [Full Replacement / Full Refund options, next steps, human review notice, 1–2 business day timeline]"
>
> **Agent — Tool-use loop**
> - No tools called
> - Reply: "I'm sorry to hear your parcel was left in the rain! To assist you properly, I need: 1. Order ID 2. What's inside? Once you provide the order ID, I can check shipping status, review our damage policy..."

---

## Answer

### The surprising result: the workflow won this round

The workflow gave the **more complete and immediately useful reply**. The agent gave a weaker one. That is the opposite of what the scenario description suggests should happen — here is why.

### Workflow — what it did

1. Classified the inquiry as `damage` (correct).
2. Called `lookup_policy(topic='damage')` — retrieved the actual policy text.
3. Produced a full reply with: both options (replacement or refund), exact next steps (order ID + photo), the human-review caveat, and the 1–2 business day timeline.

That is a **complete, actionable response**. The customer knows exactly what to do.

### Agent — what it did

It called **zero tools**. It asked for the order ID before doing anything, saying "once you give me the order ID, I *can* check shipping and review the damage policy" — but it did not actually do any of that yet.

From a customer's perspective, the workflow reply is better here.

---

### Why this happened

The scenario description in `scenarios.py` says:

> "Novel intent: damaged delivery with no matching workflow template. The agent reasons from policy and escalates; the workflow gives a generic reply."

That description is **out of date**. The `damage` intent has a perfectly good template in `_TEMPLATE_SYSTEMS` in `workflow.py`. So the workflow did not fall back to the generic reply — it routed to a well-designed template that called the right tool and produced a solid answer.

The agent, on the other hand, decided it needed the order ID before acting. That is a reasonable instinct (you cannot look up shipping without an order ID), but it made the agent *more cautious and less immediately helpful* than the workflow.

---

### What this means for the demo

The "novel" scenario does not clearly demonstrate the agent's advantage right now. The scenario that *does* show the workflow's structural weakness is **compound** — where the workflow classifies `address_change`, handles only that, and silently drops the "if not possible, cancel it" fallback. The agent follows the conditional through.

The "novel" scenario would only expose the workflow's limits if the inquiry truly fell outside all its templates (e.g. a completely unrecognized intent landing in the `other` bucket → generic fallback). As written, `damage` is anticipated and the template handles it well.

---

### Summary

| | Workflow | Agent |
|---|---|---|
| Tools called | `lookup_policy('damage')` ✓ | None |
| Policy info given | Full policy text used ✓ | Not yet — pending order ID |
| Customer reply quality | Complete and actionable ✓ | Incomplete — asks for more before helping |
| Scenario description accuracy | Does not match — workflow did well | Does not match — agent underperformed |

**Takeaway:** The workflow behaved exactly as its author intended, because the author anticipated `damage` and wrote a good template. The agent was overly cautious. The compound scenario is the cleaner demonstration of the architectural difference between scripted-LLM workflows and agents.
