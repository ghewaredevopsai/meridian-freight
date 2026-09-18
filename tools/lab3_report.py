#!/usr/bin/env python3
"""lab3_report - build Lab 3's pattern comparison from your saved prompts.

    python3 tools/lab3_report.py              # print the table
    python3 tools/lab3_report.py --record     # also write lab-3-record.md

Save each prompt you sent as its own file, then run this:

    prompt-bare.txt        the task on its own                          1 turn
    prompt-fewshot.txt     the task preceded by two worked examples     1 turn
    prompt-decomp.txt      the three decomposition requests, together   3 turns
    prompt-critique.txt    the task plus the "find three ways" follow-up 2 turns

It meters what you typed, and then what each pattern actually SENT. The attachments
(manifest.py and the runbook) go again with every turn of a chat, so a three-turn
pattern pays for them three times - that, not the wording, is most of its cost.

The sent column is a FLOOR: it leaves out the model's own earlier replies, which
are re-sent too from the second turn on and which no file here can see.

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
    ("bare", "prompt-bare.txt", 1),
    ("few-shot", "prompt-fewshot.txt", 1),
    ("decomposition", "prompt-decomp.txt", 3),
    ("self-critique", "prompt-critique.txt", 2),
]

ATTACHMENTS = [REPO / "meridian" / "manifest.py", REPO / "docs" / "ops-runbook.md"]


def meter(path: Path) -> int:
    return estimate_tokens(path.read_text(encoding="utf-8"), classify(path))


def rows():
    attached = sum(meter(p) for p in ATTACHMENTS)
    out = []
    for name, fname, turns in PATTERNS:
        path = REPO / fname
        if path.exists():
            typed = meter(path)
            out.append((name, fname, typed, turns, turns * attached + typed))
        else:
            out.append((name, fname, None, turns, None))
    return attached, out


def _vs(name, sent, base):
    if name == "bare":
        return "baseline"
    return "%.1fx" % (sent / base) if (sent and base) else "-"


def table(attached, data) -> str:
    base = next((s for n, _, _, _, s in data if n == "bare" and s), None)
    fmt = "%-15s %-20s %7s %6s %11s   %s"
    lines = [fmt % ("pattern", "file", "typed", "turns", "est. sent", "vs bare"),
             "-" * 76]
    for name, fname, typed, turns, sent in data:
        if typed is None:
            lines.append(fmt % (name, fname, "-", turns, "-", "not saved yet"))
        else:
            lines.append(fmt % (name, fname, typed, turns, sent, _vs(name, sent, base)))
    lines += ["",
              "  est. sent = turns x %d (manifest.py + runbook, re-sent every turn) + typed."
              % attached,
              "  a floor: the model's earlier replies are re-sent too, and are not counted."]
    if not base:
        lines += ["", "  save prompt-bare.txt to get the comparison column"]
    return "\n".join(lines)


def record(data) -> str:
    base = next((s for n, _, _, _, s in data if n == "bare" and s), None)
    body = []
    for name, _, typed, turns, sent in data:
        body.append("%-15s ___ / 3        %6s  %5s  %9s   %s" % (
            name, "-" if typed is None else typed, turns,
            "-" if sent is None else sent, _vs(name, sent, base)))

    return ("""# Lab 3

pattern         defects found   typed  turns  est. sent   vs bare
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
    attached, data = rows()
    print()
    print(table(attached, data))
    print()
    missing = [f for _, f, t, _, _ in data if t is None]
    if missing:
        print("  not saved yet: " + ", ".join(missing))
        print("  (you only run two patterns yourself - your partner's two stay blank")
        print("   until you swap sheets)")
        print()
    if "--record" in sys.argv:
        out = REPO / "lab-3-record.md"
        out.write_text(record(data), encoding="utf-8")
        print(f"  wrote {out.name} - fill in the defect counts and the two questions")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
