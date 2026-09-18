#!/usr/bin/env python3
"""audit_report - the token audit's four cuts, measured in one command.

    python3 tools/audit_report.py              # print the table
    python3 tools/audit_report.py --record     # also write lab-3-record.md

Meters the baseline bundle and each cut, and works out what share of the baseline
each one is. It generates `six-lines.txt` for you if cut 2 needs it.

**It cannot tell you whether the answer was still right.** That is the column the lab
is actually about, and the only one a person has to fill in - so this fills in the
arithmetic and leaves you the judgement.

Cut 3 is not a change of attachments at all: it is starting a new chat. Its saving is
the conversation you stop re-sending, which no bundle can show, so the table reports
it separately from `ctxmeter turns`.

Standard library only.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from ctxmeter import classify, estimate_tokens  # noqa: E402

CUTS = [
    ("baseline", "naive.txt", "what most people attach"),
    ("cut 1", "cut1-no-data.txt", "drop the two data files"),
    ("cut 2", "cut2-rule-not-docs.txt", "the rule, not all of docs/"),
    ("cut 4", "cut4-one-file.txt", "one file, far too little"),
]


def ensure_six_lines() -> None:
    """Cut 2 attaches the Charging order section; make it if it is not there."""
    target = REPO / "six-lines.txt"
    if target.exists():
        return
    runbook = (REPO / "docs" / "ops-runbook.md").read_text(encoding="utf-8")
    keep, out = False, []
    for line in runbook.splitlines():
        if line.startswith("## Charging order"):
            keep = True
        elif line.startswith("## Clocks"):
            keep = False
        if keep:
            out.append(line)
    target.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"  (generated six-lines.txt, {len(out)} lines, for cut 2)")


def bundle_total(name: str) -> int | None:
    path = REPO / "tools" / "bundles" / name
    if not path.exists():
        return None
    total = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        matches = sorted(REPO.glob(line)) if any(c in line for c in "*?[") else [REPO / line]
        for m in matches:
            if m.is_file():
                total += estimate_tokens(m.read_text(encoding="utf-8", errors="replace"),
                                         classify(m))
    return total or None


def conversation_cost() -> str:
    r = subprocess.run([sys.executable, str(REPO / "tools" / "ctxmeter.py"), "turns",
                        "tools/bundles/cut2-rule-not-docs.txt", "--turns", "6"],
                       capture_output=True, text=True, cwd=REPO)
    for line in r.stdout.splitlines():
        if "turns cost about" in line:
            return line.strip()
    return "run: python3 tools/ctxmeter.py turns tools/bundles/cut2-rule-not-docs.txt --turns 6"


def main() -> int:
    ensure_six_lines()
    base = bundle_total("naive.txt")
    print()
    print("%-10s %-26s %10s  %9s   %s"
          % ("", "what changed", "est. tok", "of baseline", "answer still right?"))
    print("-" * 78)
    for label, fname, desc in CUTS:
        total = bundle_total(fname)
        if total is None:
            print("%-10s %-26s %10s  %9s   %s" % (label, desc, "-", "-", "(bundle missing)"))
            continue
        share = "100%" if label == "baseline" else "%.0f%%" % (100 * total / base)
        print("%-10s %-26s %10d  %9s   %s" % (label, desc, total, share, "___"))
        if label == "cut 2":
            print("%-10s %-26s %10s  %9s   %s"
                  % ("cut 3", "start a new chat", "same", "same", "___"))
    print()
    print("  cut 3 changes no attachment - it drops the conversation you keep re-sending:")
    print("    " + conversation_cost())
    print()
    print("  largest cut that kept the answer is yours to decide - that is the lab.")
    print()

    if "--record" in sys.argv:
        lines = []
        for label, fname, desc in CUTS:
            total = bundle_total(fname)
            share = ("100%" if label == "baseline"
                     else ("%.0f%%" % (100 * total / base) if total else "____"))
            lines.append("%-10s %-27s %8s  %6s   ___"
                         % (label, desc, total or "____", share))
            if label == "cut 2":
                lines.append("%-10s %-27s %8s  %6s   ___" % ("cut 3", "start a new chat", "same", "same"))
        (REPO / "lab-3-record.md").write_text("""# Lab 3

                                       est. tok   share   answer still right?
""" + "\n".join(lines) + """

Largest cut that kept the answer: ____%
The cut that broke it, and why:
____________________________________________________________

Did ctxmeter refuse a percentage on the diff?  ___   Why?
____________________________________________________________

What the meter could NOT see on any of these runs:
____________________________________________________________
""", encoding="utf-8")
        print("  wrote lab-3-record.md - fill in the correctness column and the three questions")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
