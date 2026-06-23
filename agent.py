"""
Agent: a ReAct-style tool-use loop where the model decides what to call next.

The author wrote the goal and the rules.  The model writes the execution path.
Locus of control: the model.
"""

import os
from dotenv import load_dotenv
import anthropic
import tools as T

load_dotenv()

MODEL = "claude-haiku-4-5-20251001"
MAX_ITERATIONS = 6

_AGENT_SYSTEM = """\
You are a customer-service agent for an online store.
Resolve the customer's inquiry fully using the available tools.

Guidelines:
- Work through the problem step by step. Call tools to gather the facts you need.
- If the customer states a conditional fallback ("if X is not possible, do Y"),
  evaluate X first, then — if X is indeed not possible — pursue Y.
- Address EVERY part of the inquiry, including conditional follow-ups.
- If a case requires human review per policy (e.g. damage, complex eligibility),
  end your reply with [ESCALATE] and explain what the human needs to confirm.
- Do not invent or guess policy eligibility — look it up with lookup_policy.
- Keep the final reply concise and actionable.

You have a maximum of 6 tool calls."""


def run_agent(inquiry: str) -> None:
    client = anthropic.Anthropic()
    msgs = [{"role": "user", "content": inquiry}]

    for _ in range(MAX_ITERATIONS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            temperature=0,
            system=_AGENT_SYSTEM,
            tools=T.TOOL_DEFINITIONS,
            messages=msgs,
        )

        if response.stop_reason == "end_turn":
            print(f"\n  [reply]\n  {_text(response)}")
            return

        if response.stop_reason == "tool_use":
            msgs.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    print(f"  [tool] {block.name}({T.fmt_args(block.input)})")
                    result = T.execute_tool(block.name, block.input)
                    print(f"  [tool] -> {result}")
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        }
                    )

            msgs.append({"role": "user", "content": tool_results})
            continue

        # Unexpected stop reason
        print(f"  [warning] unexpected stop_reason={response.stop_reason!r}")
        print(f"\n  [reply]\n  {_text(response)}")
        return

    # Hit the iteration cap — ask for a best-effort final reply
    print(f"  [warning] reached {MAX_ITERATIONS}-iteration cap")
    final = client.messages.create(
        model=MODEL,
        max_tokens=512,
        temperature=0,
        system=_AGENT_SYSTEM + (
            f"\n\nYou have used all {MAX_ITERATIONS} tool calls. "
            "Provide your best answer now based on what you have gathered."
        ),
        messages=msgs,
    )
    print(f"\n  [reply]\n  {_text(final)}")


def _text(response: anthropic.types.Message) -> str:
    for block in response.content:
        if hasattr(block, "text"):
            return block.text
    return "(no text in response)"
