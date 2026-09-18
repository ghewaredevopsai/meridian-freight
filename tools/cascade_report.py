#!/usr/bin/env python3
"""cascade_report - sweep the gate and show what each threshold costs.

    python3 tools/cascade_report.py              # the sweep
    python3 tools/cascade_report.py --record     # also write lab-2-record.md

Runs the twenty supplied cases through `cascade.py`'s two functions at a range of
thresholds and prints accuracy, cost and escalation rate for each, against the two
baselines. No model is called and nothing touches the network, so every row is the
same for everyone in the room.

It does NOT edit cascade.py. Write your own `decide()` there first - the thinking is
the lab - then use this to see the whole curve at once instead of running the script
six times and copying numbers.

Standard library only.
"""

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THRESHOLDS = [0.40, 0.50, 0.60, 0.65, 0.70, 0.80, 0.90, 1.01]


def load_cascade():
    spec = importlib.util.spec_from_file_location("cascade", REPO / "tools" / "cascade.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    casc = load_cascade()
    cases = json.loads((REPO / "data" / "triage-cases.json").read_text())["cases"]
    base = casc.baselines(cases)

    print()
    print("%-12s %9s %8s %11s   %s" % ("strategy", "accuracy", "cost", "escalated", "note"))
    print("-" * 70)
    print("%-12s %8.0f%% %8d %11s   %s"
          % ("always cheap", 100 * base["always_cheap"]["accuracy"],
             base["always_cheap"]["cost_minor"], "-", "wrong 3 times in 10"))
    print("%-12s %8.0f%% %8d %11s   %s"
          % ("always strong", 100 * base["always_strong"]["accuracy"],
             base["always_strong"]["cost_minor"], "all", "the baseline to beat"))
    print()

    strong = base["always_strong"]["cost_minor"]
    best = best_cost = None
    for t in THRESHOLDS:
        casc.decide = (lambda th: (lambda a, c, case: c < th))(t)
        r = casc.run(cases)
        note = ""
        if r["cost_minor"] > strong:
            note = "costs MORE than always-strong"
        elif r["accuracy"] >= base["always_strong"]["accuracy"]:
            if best is None:
                best, best_cost, note = t, r["cost_minor"], "cheapest at full accuracy"
            elif r["cost_minor"] == best_cost:
                note = "same cost - the plateau"
            else:
                note = "full accuracy, %.1fx the cost of %.2f" % (r["cost_minor"] / best_cost, best)
        print("%-12s %8.0f%% %8d %10.0f%%   %s"
              % ("gate < %.2f" % t, 100 * r["accuracy"], r["cost_minor"],
                 100 * r["escalation_rate"], note))

    right = [c["cheap_confidence"] for c in cases if c["cheap_answer"] == c["true_answer"]]
    wrong = [c["cheap_confidence"] for c in cases if c["cheap_answer"] != c["true_answer"]]
    print()
    print("  the assumption the whole pattern rests on:")
    print("    confidence when right %.2f  vs  when wrong %.2f  (over %d and %d cases)"
          % (sum(right) / len(right), sum(wrong) / len(wrong), len(right), len(wrong)))
    print("    if those two were equal, your gate would be a coin toss that costs money.")
    print()

    if "--record" in sys.argv:
        casc.decide = (lambda a, c, case: c < best) if best else casc.decide
        chosen = casc.run(cases) if best else None
        saving = ("%.0f%%" % (100 * (strong - chosen["cost_minor"]) / strong)) if chosen else "____"
        (REPO / "lab-2-record.md").write_text(f"""# Lab 2

threshold   accuracy   cost   escalated
0.40        ____       ____   ____
0.60        ____       ____   ____
0.80        ____       ____   ____
1.01        ____       ____   ____

Cheapest threshold at 100% accuracy: {best if best else '____'}
Cost there vs always-strong: {saving} saving

Escalate-everything cost ______ against always-strong's {strong}.

Confidence when right {sum(right)/len(right):.2f} vs when wrong {sum(wrong)/len(wrong):.2f}.
Would this cascade work if those two numbers were equal?  ______

--- fill this in yourself ---

At what price ratio between the two models does the cascade stop being worth
its complexity?
____________________________________________________________
""", encoding="utf-8")
        print("  wrote lab-2-record.md - fill in the four sweep rows and the last question")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
