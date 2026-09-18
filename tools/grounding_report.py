#!/usr/bin/env python3
"""grounding_report - the three groundings, measured before you send anything.

    python3 tools/grounding_report.py              # the three sizes
    python3 tools/grounding_report.py --record     # also write lab-4-record.md

Meters the three ways of grounding the same question:

    A  everything          the whole repository, as cloned
    B  two files           rating.py and manifest.py
    C  the rule            the Charging order section, the fuel lines from both
                           files, and the failing test output

It generates the three files C needs.  C carries the rule AND the code it governs,
so a C answer that names the drift has matched one to the other - not just read the
rule back. C shows no surcharges, so it cannot find the two that manifest.py omits.

A counts the files git tracks, so your own lab files do not inflate it and everyone's
figure matches. With no git, it falls back to every file in the folder. **It cannot tell you whether each answer named the
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


FUEL_LINES = {
    "meridian/rating.py": ("subtotal = sum(", "fuel = (", "total_minor="),
    "meridian/manifest.py": ("fuel = (", "return base + fuel"),
}


def tracked() -> list[Path]:
    """The repository as cloned: git's file list, or the folder if there is no git."""
    r = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=REPO)
    if r.returncode == 0 and r.stdout.strip():
        files = [REPO / line for line in r.stdout.splitlines()]
    else:
        files = [p for p in sorted(REPO.rglob("*")) if ".git" not in p.parts]
    return [p for p in files if p.is_file()
            and p.suffix in {".py", ".json", ".md", ".txt"}
            and p.name not in {"six-lines.txt", "fuel-lines.txt", "failing-test.txt"}]


def build_c() -> list[Path]:
    """Cut C is the runbook rule, the fuel lines it governs, and the failing test."""
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
        tail = [line.replace(str(REPO) + "/", "") for line in tail]
        failing.write_text("\n".join(tail) + "\n", encoding="utf-8")

    fuel = REPO / "fuel-lines.txt"
    if not fuel.exists():
        out = []
        for rel, starts in FUEL_LINES.items():
            out.append(f"# {rel}")
            for line in (REPO / rel).read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(starts):
                    out.append(line.strip())
            out.append("")
        fuel.write_text("\n".join(out), encoding="utf-8")
    return [six, fuel, failing]


def main() -> int:
    everything = tracked()
    two = [REPO / "meridian" / "rating.py", REPO / "meridian" / "manifest.py"]
    rule = build_c()

    rows = [("A", "everything", "the whole repository", meter(everything)),
            ("B", "two files", "rating.py + manifest.py", meter(two)),
            ("C", "the rule", "rule + fuel lines + failing test", meter(rule))]
    smallest = min(t for *_, t in rows)

    print()
    print("%-3s %-12s %-34s %10s %9s   %s"
          % ("", "grounding", "what you attach", "est. tok", "vs C", "named the drift?"))
    print("-" * 92)
    for label, name, what, tokens in rows:
        print("%-3s %-12s %-34s %10d %8.0fx   %s"
              % (label, name, what, tokens, tokens / smallest, "___"))
    print()
    print("  C's files are ready: six-lines.txt, fuel-lines.txt and failing-test.txt -")
    print("  paste those three, attach nothing.")
    print("  the last column is yours. it is the whole lab.")
    print()

    if "--record" in sys.argv:
        (REPO / "lab-4-record.md").write_text("""# Lab 4

                       est. tokens sent   named the drift?   also found the two
                                                             missing surcharges?
A: everything          %-18d ___                ___
B: two files           %-18d ___                ___
C: the rule            %-18d ___                n/a - C shows no surcharges

Ratio of A to C: %.0f times the context.
Which gave the most useful answer? ______

If A lost, what did it spend its attention on instead?
____________________________________________________________
""" % (rows[0][3], rows[1][3], rows[2][3], rows[0][3] / rows[2][3]), encoding="utf-8")
        print("  wrote lab-4-record.md - fill in the yes/no columns and the last two questions")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
