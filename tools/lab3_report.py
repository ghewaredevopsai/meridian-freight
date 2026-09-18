#!/usr/bin/env python3
"""lab3_report - build Lab 3's pattern comparison from your saved prompts.

    python3 tools/lab3_report.py              # print the table
    python3 tools/lab3_report.py --record     # also write lab-3-record.md

Save each prompt you sent as its own file, then run this:

    prompt-bare.txt        the task on its own
    prompt-fewshot.txt     the task preceded by two worked examples
    prompt-decomp.txt      the three decomposition requests, together
    prompt-critique.txt    the task plus the "find three ways you were wrong" follow-up

It meters each one and shows what the pattern cost relative to the bare version. The
attachments are identical across runs, so that difference IS the cost of the pattern.

**It cannot count defects for you.** How many of the three money defects each pattern
surfaced is a judgement, and it is the column that matters - the script fills in the
arithmetic so you can spend the time on that.

Standard library only.
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from ctxmeter import classify, estimate_tokens  # noqa: E402

PATTERNS = [
    ("bare", "prompt-bare.txt"),
    ("few-shot", "prompt-fewshot.txt"),
    ("decomposition", "prompt-decomp.txt"),
    ("self-critique", "prompt-critique.txt"),
]


def rows():
    out = []
    for name, fname in PATTERNS:
        path = REPO / fname
        if path.exists():
            text = path.read_text(encoding="utf-8")
            out.append((name, fname, estimate_tokens(text, classify(path))))
        else:
            out.append((name, fname, None))
    return out


def table(data) -> str:
    base = next((t for n, _, t in data if n == "bare" and t), None)
    lines = ["%-15s %-20s %10s   %s" % ("pattern", "file", "est. tokens", "vs bare"),
             "-" * 62]
    for name, fname, tokens in data:
        if tokens is None:
            lines.append("%-15s %-20s %10s   %s" % (name, fname, "-", "not saved yet"))
        elif base:
            lines.append("%-15s %-20s %10d   %s"
                         % (name, fname, tokens, "baseline" if name == "bare"
                            else "%.1fx" % (tokens / base)))
        else:
            lines.append("%-15s %-20s %10d   %s" % (name, fname, tokens, "-"))
    if not base:
        lines += ["", "  save prompt-bare.txt to get the comparison column"]
    return "\n".join(lines)


def record(data) -> str:
    base = next((t for n, _, t in data if n == "bare" and t), None)
    body = []
    for name, _, tokens in data:
        cost = "-" if tokens is None else str(tokens)
        rel = "baseline" if name == "bare" else (
            "%.1fx" % (tokens / base) if (tokens and base) else "-")
        body.append("%-15s ___ / 3        %8s      %-9s ___" % (name, cost, rel))

    return ("""# Lab 3

pattern         defects found  est. tokens   vs bare   turns
""" + "\n".join(body) + """

The three money defects in manifest.py:
1. ____________________________________________________________
2. ____________________________________________________________
3. ____________________________________________________________

Cheapest pattern that found all three: ______________

The pattern I will actually use at work, and for what:
____________________________________________________________
""")


def main() -> int:
    data = rows()
    print()
    print(table(data))
    print()
    missing = [f for _, f, t in data if t is None]
    if missing:
        print("  not saved yet: " + ", ".join(missing))
        print("  (you only run two patterns yourself - your partner's two stay blank")
        print("   until you swap sheets)")
        print()
    if "--record" in sys.argv:
        out = REPO / "lab-3-record.md"
        out.write_text(record(data), encoding="utf-8")
        print(f"  wrote {out.name} - fill in the defect counts, turns and the two questions")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
