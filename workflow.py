"""
Scripted-LLM workflow: one classification call, then one fixed template path.

The author wrote the flowchart. The model executes steps the author pre-decided.
Locus of control: the author.
"""

import os
from dotenv import load_dotenv
import anthropic
import tools as T

load_dotenv()

MODEL = "claude-sonnet-4-6"

# ── Classification ────────────────────────────────────────────────────────────

_CLASSIFY_SYSTEM = """\
You are a customer-support triage classifier for an e-commerce store.
Classify the customer inquiry into exactly ONE of these intents:

  shipping_status   customer asks where their order is or when it arrives
  address_change    customer wants to change delivery address, date, or time slot
  cancel_refund     customer wants to cancel an order and/or receive a refund
  damage            customer reports a damaged, soaked, or mishandled delivery
  returns           customer wants to return a delivered item
  other             does not clearly fit any category above

Rules:
- If the message expresses a PRIMARY intent plus a conditional fallback
  ("if X isn't possible, do Y"), classify the PRIMARY intent only.
- Reply with ONLY the intent name — no punctuation, no explanation."""

_VALID_INTENTS = {
    "shipping_status", "address_change", "cancel_refund",
    "damage", "returns", "other",
}


def _classify(client: anthropic.Anthropic, inquiry: str) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=20,
        temperature=0,
        system=_CLASSIFY_SYSTEM,
        messages=[{"role": "user", "content": inquiry}],
    )
    raw = resp.content[0].text.strip().lower()
    for intent in _VALID_INTENTS:
        if intent in raw:
            return intent
    return "other"


# ── Template system prompts ───────────────────────────────────────────────────
# Each template is focused on exactly one intent.  The address_change template
# deliberately does not address any other part of the inquiry — that is the
# honest structural constraint, not a strawman.

_TEMPLATE_SYSTEMS: dict[str, str | None] = {
    "shipping_status": """\
You are a customer-service agent for an online store.
The customer is asking about their order's shipping status.
Use get_shipping_status to look up the order ID mentioned in the inquiry,
then write a brief, friendly reply covering the current state and estimated arrival.
Address only the shipping-status question.""",

    "address_change": """\
You are a customer-service agent for an online store.
The customer is requesting a delivery address or date change.
Use get_shipping_status to check whether the order can still be redirected
(can_change_address field and current state).
If the address change is no longer possible, politely explain why.
Address ONLY the address-change request — do not speculate about or resolve
any other topic the customer may have mentioned.""",

    "cancel_refund": """\
You are a customer-service agent for an online store.
The customer wants to cancel their order and/or receive a refund.
Use lookup_policy with topic='cancellation' to retrieve the relevant policy,
then write a concise reply explaining next steps and the refund timeline.""",

    "damage": """\
You are a customer-service agent for an online store.
The customer is reporting a damaged or mishandled delivery.
Use lookup_policy with topic='damage' to retrieve the damage resolution policy,
then write a sympathetic reply explaining the customer's options.
Make clear that this case requires human review before anything is confirmed.""",

    "returns": """\
You are a customer-service agent for an online store.
The customer wants to return a delivered item.
Use lookup_policy with topic='returns' to get the return policy,
then write a clear, step-by-step reply explaining the return process.""",

    "other": None,  # generic fallback — no tool call, no LLM template
}

_GENERIC_FALLBACK = (
    "Thank you for reaching out. Your message has been received and "
    "a customer-service representative will get back to you shortly."
)


# ── Template runner ───────────────────────────────────────────────────────────

def _run_template(
    client: anthropic.Anthropic,
    inquiry: str,
    system: str,
) -> str:
    """Execute the template: at most ONE tool call, then a final text reply."""
    msgs = [{"role": "user", "content": inquiry}]

    r1 = client.messages.create(
        model=MODEL,
        max_tokens=512,
        temperature=0,
        system=system,
        tools=T.TOOL_DEFINITIONS,
        messages=msgs,
    )

    if r1.stop_reason != "tool_use":
        return _text(r1)

    # Execute the first (and only) tool call
    tool_block = next(b for b in r1.content if b.type == "tool_use")
    print(f"  [tool] {tool_block.name}({T.fmt_args(tool_block.input)})")
    result = T.execute_tool(tool_block.name, tool_block.input)
    print(f"  [tool] -> {result}")

    msgs = msgs + [
        {"role": "assistant", "content": r1.content},
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result,
                }
            ],
        },
    ]

    # Second call without tools so the model must produce a text reply
    r2 = client.messages.create(
        model=MODEL,
        max_tokens=512,
        temperature=0,
        system=system,
        messages=msgs,
    )
    return _text(r2)


def _text(response: anthropic.types.Message) -> str:
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return "(no text in response)"


# ── Public entry point ────────────────────────────────────────────────────────

def run_workflow(inquiry: str) -> None:
    client = anthropic.Anthropic()

    intent = _classify(client, inquiry)
    print(f"  [classify] intent = {intent}")

    system = _TEMPLATE_SYSTEMS.get(intent)
    if system is None:
        print(f"\n  [reply]\n  {_GENERIC_FALLBACK}")
        return

    reply = _run_template(client, inquiry, system)
    print(f"\n  [reply]\n  {reply}")
