#!/usr/bin/env python3
"""grounding_report - the three groundings, measured before you send anything.

    python3 tools/grounding_report.py              # the three sizes
    python3 tools/grounding_report.py --record     # also write lab-4-record.md

Meters the three ways of grounding the same question:

    A  everything          the whole repository
    B  two files           rating.py and manifest.py
    C  the rule            the Charging order lines, plus the failing test output

It generates the files C needs. **It cannot tell you whether each answer named the
fuel drift** - that is the column the lab is about, and the one you fill in.

Measure first, then send. Knowing the ratio before you see the answers is what stops
you talking yourself into a number afterwards.

Standard library only.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from ctxmeter import classify, estimate_tokens  # noqa: E402


def meter(paths) -> int:
    return sum(estimate_tokens(p.read_text(encoding="utf-8", errors="replace"), classify(p))
               for p in paths if p.is_file())


def build_c() -> list[Path]:
    """Cut C is the runbook rule plus the failing test output; make both."""
    six = REPO / "six-lines.txt"
    if not six.exists():
        text = (REPO / "docs" / "ops-runbook.md").read_text(encoding="utf-8")
        keep, out = False, []
        for line in text.splitlines():
            if line.startswith("## Charging order"):
                keep = True
            elif line.startswith("## Clocks"):
                keep = False
            if keep:
                out.append(line)
        six.write_text("\n".join(out) + "\n", encoding="utf-8")

    failing = REPO / "failing-test.txt"
    if not failing.exists():
        r = subprocess.run([sys.executable, "-m", "unittest", "tests.test_manifest", "-v"],
                           capture_output=True, text=True, cwd=REPO)
        tail = (r.stderr or r.stdout).strip().splitlines()[-12:]
        failing.write_text("\n".join(tail) + "\n", encoding="utf-8")
    return [six, failing]


def main() -> int:
    everything = [p for p in sorted(REPO.rglob("*"))
                  if p.is_file() and ".git" not in p.parts
                  and p.suffix in {".py", ".json", ".md", ".txt"}
                  and "six-lines" not in p.name and "failing-test" not in p.name]
    two = [REPO / "meridian" / "rating.py", REPO / "meridian" / "manifest.py"]
    rule = build_c()

    rows = [("A", "everything", "the whole repository", meter(everything)),
            ("B", "two files", "rating.py + manifest.py", meter(two)),
            ("C", "the rule", "six-lines.txt + failing-test.txt", meter(rule))]
    smallest = min(t for *_, t in rows)

    print()
    print("%-3s %-12s %-34s %10s %9s   %s"
          % ("", "grounding", "what you attach", "est. tok", "vs C", "named the drift?"))
    print("-" * 92)
    for label, name, what, tokens in rows:
        print("%-3s %-12s %-34s %10d %8.0fx   %s"
              % (label, name, what, tokens, tokens / smallest, "___"))
    print()
    print("  C's files are ready: six-lines.txt and failing-test.txt - paste those, attach nothing.")
    print("  the last column is yours. it is the whole lab.")
    print()

    if "--record" in sys.argv:
        (REPO / "lab-4-record.md").write_text("""# Lab 4

                       est. tokens sent   named the drift?   also found the two
                                                             missing surcharges?
A: everything          %-18d ___                ___
B: two files           %-18d ___                ___
C: the rule            %-18d ___                ___

Ratio of A to C: %.0f times the context.
Which gave the most useful answer? ______

If A lost, what did it spend its attention on instead?
____________________________________________________________
""" % (rows[0][3], rows[1][3], rows[2][3], rows[0][3] / rows[2][3]), encoding="utf-8")
        print("  wrote lab-4-record.md - fill in the two yes/no columns and the last question")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
