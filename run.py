"""
CLI entry point.

Usage:
  python run.py simple
  python run.py compound
  python run.py novel
  python run.py --live          # type your own inquiry
"""

import sys
import textwrap
from scenarios import SCENARIOS
import workflow
import agent

WIDTH = 64


def _bar(title: str) -> None:
    print(f"\n{'─' * WIDTH}")
    print(f"  {title}")
    print(f"{'─' * WIDTH}\n")


def _run(scenario_name: str, inquiry: str) -> None:
    _bar(f"INQUIRY  [{scenario_name.upper()}]")
    for line in textwrap.wrap(inquiry, width=WIDTH - 4):
        print(f"  {line}")

    _bar("WORKFLOW")
    workflow.run_workflow(inquiry)

    _bar("AGENT")
    agent.run_agent(inquiry)

    print(f"\n{'═' * WIDTH}\n")


def main() -> None:
    if len(sys.argv) < 2:
        names = ", ".join(SCENARIOS.keys())
        print(f"Usage: python run.py <scenario>  [{names}, --live]")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "--live":
        try:
            inquiry = input("Inquiry: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            sys.exit(0)
        if not inquiry:
            print("No inquiry entered.")
            sys.exit(1)
        _run("live", inquiry)

    elif mode in SCENARIOS:
        s = SCENARIOS[mode]
        print(f"\nScenario: {s['description']}")
        _run(mode, s["inquiry"])

    else:
        names = ", ".join(SCENARIOS.keys())
        print(f"Unknown scenario {mode!r}. Available: {names}, --live")
        sys.exit(1)


if __name__ == "__main__":
    main()
