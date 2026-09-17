#!/usr/bin/env python3
"""cascade - route the cheap work to the cheap model, and prove it was worth it.

    python3 tools/cascade.py

There is no model here and no network. The two "models" below are ordinary Python
functions with a known accuracy and a known price, so every run in the room gives
the same numbers and the arithmetic is the only thing under discussion.

YOUR JOB is `decide()`. It sees what the cheap model returned and its own
confidence, and it decides whether to accept that or pay for the strong model.

Then read the table. There are three ways to be wrong here and only one of them
looks like a saving:

  - escalate too rarely  -> you keep the cheap model's mistakes
  - escalate too often   -> you pay for the strong model AND the cheap one
  - escalate at random   -> you do both, and cannot explain either
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CASES = REPO / "data" / "triage-cases.json"

#: Price per call, in the same minor units the freight desk uses. The strong model
#: is twelve times the price, which is the ratio that makes this interesting.
COST_CHEAP_MINOR = 4
COST_STRONG_MINOR = 48


def cheap_model(case: dict) -> tuple[str, float]:
    """Fast and usually right. Returns its answer and how sure it is, 0.0 to 1.0.

    It is good at the obvious cases and it knows when it is guessing - which is
    the property the whole pattern rests on. A cheap model that is confidently
    wrong cannot be cascaded, it can only be replaced.
    """
    return case["cheap_answer"], case["cheap_confidence"]


def strong_model(case: dict) -> tuple[str, float]:
    """Slower, twelve times the price, and right on every case in this set."""
    return case["true_answer"], 1.0


def decide(answer: str, confidence: float, case: dict) -> bool:
    """Return True to escalate to the strong model.

    ---------------------------------------------------------------------------
    THIS IS THE LAB. Replace the line below.

    Start with the blunt version - escalate when confidence is under some
    threshold - then find the threshold that earns its money. Print the table for
    several thresholds before you settle on one.
    ---------------------------------------------------------------------------
    """
    return False


def run(cases: list[dict]) -> dict:
    correct = escalated = cost = 0
    for case in cases:
        answer, confidence = cheap_model(case)
        cost += COST_CHEAP_MINOR
        if decide(answer, confidence, case):
            escalated += 1
            answer, _ = strong_model(case)
            cost += COST_STRONG_MINOR
        if answer == case["true_answer"]:
            correct += 1
    n = len(cases)
    return {"n": n, "correct": correct, "accuracy": correct / n,
            "escalated": escalated, "escalation_rate": escalated / n,
            "cost_minor": cost}


def baselines(cases: list[dict]) -> dict:
    n = len(cases)
    cheap_correct = sum(1 for c in cases if c["cheap_answer"] == c["true_answer"])
    return {
        "always_cheap": {"accuracy": cheap_correct / n,
                         "cost_minor": n * COST_CHEAP_MINOR},
        "always_strong": {"accuracy": 1.0, "cost_minor": n * COST_STRONG_MINOR},
    }


def main() -> int:
    if not CASES.exists():
        print(f"cascade: no case file at {CASES}")
        return 2
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    base = baselines(cases)
    mine = run(cases)

    print("%-16s %9s %12s %12s" % ("strategy", "accuracy", "cost", "escalated"))
    print("%-16s %8.0f%% %12d %12s"
          % ("always cheap", 100 * base["always_cheap"]["accuracy"],
             base["always_cheap"]["cost_minor"], "-"))
    print("%-16s %8.0f%% %12d %12s"
          % ("always strong", 100 * base["always_strong"]["accuracy"],
             base["always_strong"]["cost_minor"], "all"))
    print("%-16s %8.0f%% %12d %11.0f%%"
          % ("your cascade", 100 * mine["accuracy"], mine["cost_minor"],
             100 * mine["escalation_rate"]))

    strong_cost = base["always_strong"]["cost_minor"]
    saved = strong_cost - mine["cost_minor"]
    lost = base["always_strong"]["accuracy"] - mine["accuracy"]
    print(f"\n  against always-strong: {100 * saved / strong_cost:+.0f}% cost, "
          f"{-100 * lost:+.0f} points of accuracy")
    if mine["escalation_rate"] == 0:
        print("  you escalated nothing - this is the cheap model with extra steps")
    elif mine["cost_minor"] >= strong_cost:
        print("  you paid MORE than always-strong: the cheap call is pure waste "
              "on every case you escalated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
