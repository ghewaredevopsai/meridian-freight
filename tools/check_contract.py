#!/usr/bin/env python3
"""check_contract - does this answer have the shape you asked for?

    python3 tools/check_contract.py answer.json

Exits 0 if the file satisfies the contract, 1 if it does not, and prints one line
per violation.

IT JUDGES SHAPE, NOT QUALITY. It cannot tell you whether the exceptions listed are
the right ones, whether the actions are sensible, or whether the model understood
the question. It tells you whether the thing that came back can be fed to the next
system without a human reading it first. That is a lower bar than "good", and it is
the bar that decides whether you can automate the step.

Standard library only. No network.
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from meridian.validate import EXCEPTION_CODES  # noqa: E402

CONSIGNMENT_ID = re.compile(r"^MF-\d{4}$")
REQUIRED_TOP = ("generated_for", "exceptions", "total")
REQUIRED_ROW = ("consignment", "codes", "action")
ACTION_MAX = 120


def check(text: str) -> list[str]:
    """Every way this answer breaks the contract, in the order a reader meets them."""
    problems: list[str] = []

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"not valid JSON: {exc}",
                "  (a fenced code block, a preamble or a trailing note all land here)"]

    if not isinstance(payload, dict):
        return [f"top level is {type(payload).__name__}, must be an object"]

    for key in REQUIRED_TOP:
        if key not in payload:
            problems.append(f"missing top-level key: {key}")

    rows = payload.get("exceptions")
    if not isinstance(rows, list):
        problems.append("'exceptions' must be a list")
        return problems

    for index, row in enumerate(rows):
        where = f"exceptions[{index}]"
        if not isinstance(row, dict):
            problems.append(f"{where} is {type(row).__name__}, must be an object")
            continue
        for key in REQUIRED_ROW:
            if key not in row:
                problems.append(f"{where} missing key: {key}")

        cid = row.get("consignment")
        if isinstance(cid, str) and not CONSIGNMENT_ID.match(cid):
            problems.append(f"{where}.consignment '{cid}' is not in the form MF-0000")

        codes = row.get("codes")
        if not isinstance(codes, list) or not codes:
            problems.append(f"{where}.codes must be a non-empty list")
        else:
            for code in codes:
                if code not in EXCEPTION_CODES:
                    problems.append(
                        f"{where}.codes has '{code}', which is not one of the six: "
                        + ", ".join(sorted(EXCEPTION_CODES)))

        action = row.get("action")
        if isinstance(action, str) and len(action) > ACTION_MAX:
            problems.append(f"{where}.action is {len(action)} chars, limit is {ACTION_MAX}")

    total = payload.get("total")
    if isinstance(total, int) and total != len(rows):
        problems.append(f"'total' says {total} but there are {len(rows)} rows")

    return problems


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    path = Path(argv[0])
    if not path.exists():
        print(f"check_contract: no such file: {path}")
        print()
        print("  This reads a file - it cannot see your chat window.")
        print()
        print("  Easiest: copy the reply, then File > New File in your editor, paste,")
        print(f"  and save it as {path} in this folder.")
        print()
        print(f"  Or in a terminal:  cat > {path}")
        print("    ...paste, press Enter so the cursor is on an empty line, then Ctrl-D.")
        print("    Nothing is printed while it waits, or when it finishes.")
        print(f"    Check it worked with: wc -c {path}   (0 bytes means nothing arrived)")
        print()
        print("  Paste the reply exactly as it came back, fence and all - whether the")
        print("  fence is there is part of what this lab measures.")
        return 2

    problems = check(path.read_text(encoding="utf-8"))
    if not problems:
        print(f"check_contract: {path} satisfies the contract")
        print("  shape only - it says nothing about whether the answer is right")
        return 0
    print(f"check_contract: {path} breaks the contract in {len(problems)} place(s)")
    for problem in problems:
        print(f"  - {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
