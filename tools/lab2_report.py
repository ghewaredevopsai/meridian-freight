#!/usr/bin/env python3
"""lab2_report - build Lab 2's comparison table from your three saved answers.

    python3 tools/lab2_report.py              # print the table
    python3 tools/lab2_report.py --record     # also write lab-2-record.md

It looks for three files in this folder, whichever of them exist:

    answer.txt         the free-prose reply        (request A)
    answer.delimited   the pipe-separated reply    (request B)
    answer.json        the JSON reply              (request C)

For each it reports the estimated size and whether it satisfies the contract, so you
do not have to run two tools three times each and copy numbers by hand. The point of
the lab is the comparison, not the clerical work.

Standard library only. It reads your files and writes at most one; nothing else.
"""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

from ctxmeter import classify, estimate_tokens  # noqa: E402

ANSWERS = [
    ("A", "prose", "answer.txt"),
    ("B", "delimited", "answer.delimited"),
    ("C", "schema", "answer.json"),
]


def contract_verdict(path: Path) -> str:
    """Run the real checker, so this agrees with what you saw in the lab."""
    r = subprocess.run([sys.executable, str(REPO / "tools" / "check_contract.py"), str(path)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return "pass"
    first = next((l.strip(" -") for l in r.stdout.splitlines() if l.strip().startswith("-")), "")
    return "fail" + (f" ({first[:34]})" if first else "")


def rows() -> list[tuple]:
    out = []
    for label, shape, name in ANSWERS:
        path = REPO / name
        if not path.exists():
            out.append((label, shape, name, None, "not saved yet"))
            continue
        text = path.read_text(encoding="utf-8")
        tokens = estimate_tokens(text, classify(path))
        out.append((label, shape, name, tokens, contract_verdict(path)))
    return out


def table(data) -> str:
    lines = ["%-3s %-11s %-17s %10s   %s" % ("", "shape", "file", "est. tokens", "contract"),
             "-" * 66]
    for label, shape, name, tokens, verdict in data:
        lines.append("%-3s %-11s %-17s %10s   %s"
                     % (label, shape, name, "-" if tokens is None else tokens, verdict))
    sized = [t for *_, t, _ in data if t]
    if len(sized) > 1 and min(sized):
        lines += ["", "  largest / smallest = %.1fx" % (max(sized) / min(sized))]
    return "\n".join(lines)


def record(data) -> str:
    def cell(shape, field):
        for _, s, _, tokens, verdict in data:
            if s == shape:
                return {"tokens": "-" if tokens is None else str(tokens),
                        "verdict": verdict}[field]
        return "?"

    sized = {s: t for _, s, _, t, _ in data if t}
    ratio = ("%.1f" % (sized["schema"] / sized["prose"])
             if {"schema", "prose"} <= sized.keys() else "____")

    return f"""# Lab 2

                     est. tokens   contract
free prose           {cell('prose','tokens'):>11}   {cell('prose','verdict')}
delimited            {cell('delimited','tokens'):>11}   {cell('delimited','verdict')}
supplied schema      {cell('schema','tokens'):>11}   {cell('schema','verdict')}

JSON vs prose: {ratio} times larger.

--- fill these in yourself ---

If a field went missing from the delimited answer, would I have noticed?
____________________________________________________________

What I changed in the request to make C pass (if it did not pass first time):
____________________________________________________________

What the contract costs, and what it buys:
____________________________________________________________
"""


def main() -> int:
    data = rows()
    print()
    print(table(data))
    print()
    missing = [n for *_, n, t, _ in data if t is None]
    if missing:
        print("  not saved yet: " + ", ".join(missing))
        print("  (save each reply as that filename, then run this again)")
        print()
    if "--record" in sys.argv:
        out = REPO / "lab-2-record.md"
        out.write_text(record(data), encoding="utf-8")
        print(f"  wrote {out.name} - open it and fill in the three questions at the foot")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
