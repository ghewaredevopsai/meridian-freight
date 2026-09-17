#!/usr/bin/env python3
"""ctxmeter - a context budget meter.

It answers one question: what are you sending, and how much of it is what?

Standard library only. It opens no network socket, starts no subprocess and
writes no file. You can read the whole thing in ten minutes, and you should,
because it is about to produce numbers you will quote to your team.

    python3 tools/ctxmeter.py diff tools/bundles/naive.txt tools/bundles/minimal.txt
    python3 tools/ctxmeter.py count --absolute meridian/rating.py meridian/manifest.py
    python3 tools/ctxmeter.py repo --absolute
    python3 tools/ctxmeter.py turns tools/bundles/naive.txt --turns 8

WHAT IT IS NOT
--------------
It is not a tokenizer. It is an estimator built from a regular expression, and
every number it prints is a floor: it counts only what you listed. The hidden
system prompt, the editor's own retrieval and whatever the agent decides to read
are invisible to it.

Use it for deltas. The counter proves the cut; the billing page proves the money;
they never go in the same row of a table.
"""

import argparse
import fnmatch
import math
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------
# The estimator
# --------------------------------------------------------------------------
# A pre-tokenizer in the shape of the one production BPE vocabularies use: split
# into contractions, letter runs, short digit runs, punctuation runs and
# whitespace runs, then charge each piece. Long pieces get split by the real
# tokenizer too, so they are charged by length.
PRETOKEN = re.compile(
    r"'(?:s|d|m|t|ll|ve|re)"      # contractions are single tokens
    r"|[ ]?[A-Za-z]+"             # a word, with its leading space
    r"|[ ]?[0-9]{1,3}"            # digits go in runs of at most three
    r"|[^\sA-Za-z0-9]+"           # punctuation runs
    r"|\s+"                       # whitespace, including newlines
)

# These four constants were not guessed. They were fitted against a real BPE
# tokenizer over every file in this repository - see tools/calibration.md for the
# method, the measured error and the date.
LONG_PIECE = 8          # pieces longer than this are split by a real tokenizer
CHARS_PER_SUBWORD = 6   # ...into roughly this many characters each
WHITESPACE_RUN = 12     # a run of blanks compresses to about one token per this
PUNCTUATION_RUN = 3     # so does a run of brackets, quotes and commas

#: Residual bias after fitting, by content class, from the same calibration run.
#: Code still reads high because identifiers split more than length predicts.
CALIBRATION = {"code": 0.86, "data": 0.95, "prose": 0.94, "config": 0.94,
               "instructions": 0.94, "prompt": 0.94, "tools": 0.95, "other": 0.91}


def estimate_tokens(text: str, kind: str = "other") -> int:
    """Estimated tokens for a string. Deterministic, and the same on every OS."""
    text = normalise(text)
    total = 0
    for piece in PRETOKEN.findall(text):
        if piece.isspace():
            total += 1 if len(piece) <= 1 else math.ceil(len(piece) / WHITESPACE_RUN)
        elif not piece[:1].isalnum() and not piece[:1].isspace():
            total += max(1, math.ceil(len(piece) / PUNCTUATION_RUN))
        elif len(piece) > LONG_PIECE:
            total += math.ceil(len(piece) / CHARS_PER_SUBWORD)
        else:
            total += 1
    return round(total * CALIBRATION.get(kind, CALIBRATION["other"]))


def normalise(text: str) -> str:
    """CRLF to LF.

    Windows line endings cost about one extra token per line against a real
    tokenizer. Half of any room is on Windows, and a measurement that changes
    because of who ran it is not a measurement.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


# --------------------------------------------------------------------------
# Content classes - why a percentage can lie
# --------------------------------------------------------------------------
CLASSES = {
    "code":   {".py", ".js", ".ts", ".java", ".go", ".rb", ".sh", ".sql"},
    "data":   {".json", ".csv", ".xml", ".yaml", ".yml", ".ndjson"},
    "prose":  {".md", ".txt", ".rst", ".adoc"},
    "config": {".toml", ".ini", ".cfg", ".env", ".gitignore"},
}


def classify(path: Path) -> str:
    suffix = path.suffix.lower()
    for name, suffixes in CLASSES.items():
        if suffix in suffixes:
            return name
    return "other"


# --------------------------------------------------------------------------
# What is actually in the bundle
# --------------------------------------------------------------------------
class Item:
    def __init__(self, label: str, tokens: int, kind: str, note: str = ""):
        self.label, self.tokens, self.kind, self.note = label, tokens, kind, note


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def load_bundle(bundle_path: Path) -> list[Path]:
    """A bundle file is a list of paths, one per line. `#` comments, blanks ignored."""
    paths = []
    for line in read(bundle_path).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        resolved = (REPO / line) if not os.path.isabs(line) else Path(line)
        matches = sorted(REPO.glob(line)) if any(ch in line for ch in "*?[") else [resolved]
        for match in matches:
            if match.is_file():
                paths.append(match)
            elif not matches or not match.exists():
                print(f"ctxmeter: bundle lists a path that is not there: {line}",
                      file=sys.stderr)
    return paths


def always_on(attached: list[Path]) -> list[Item]:
    """The instruction layer you did not attach but are paying for anyway.

    Repository-wide instruction files are sent on every request. A path-scoped
    `*.instructions.md` is sent only when its `applyTo` glob matches something in
    the request - so resolving those globs is the difference between what you
    think you sent and what went.
    """
    items: list[Item] = []
    for name in (".github/copilot-instructions.md", "AGENTS.md", "CLAUDE.md"):
        path = REPO / name
        if path.is_file():
            items.append(Item(name, estimate_tokens(read(path), "instructions"),
                              "instructions", "always on"))

    scoped_dir = REPO / ".github" / "instructions"
    if scoped_dir.is_dir():
        relative = [str(p.relative_to(REPO)) for p in attached]
        for path in sorted(scoped_dir.glob("*.instructions.md")):
            glob = apply_to(read(path))
            if glob is None:
                continue
            hits = [r for r in relative if fnmatch.fnmatch(r, glob)]
            if hits:
                items.append(Item(str(path.relative_to(REPO)),
                                  estimate_tokens(read(path), "instructions"),
                                  "instructions",
                                  f"applyTo {glob} matched {len(hits)} file(s)"))
    return items


def apply_to(text: str) -> str | None:
    """Read the applyTo glob out of a front-matter block."""
    match = re.search(r"^applyTo:\s*['\"]?([^'\"\n]+)['\"]?\s*$", text, re.M)
    return match.group(1).strip() if match else None


def tool_schemas() -> list[Item]:
    """Tool and MCP definitions are context, and they are re-sent every turn."""
    items = []
    for name in (".vscode/mcp.json", ".mcp.json"):
        path = REPO / name
        if path.is_file():
            items.append(Item(name, estimate_tokens(read(path), "tools"), "tools",
                              "re-sent every turn"))
    return items


def measure(paths: list[Path], prompt: Path | None = None,
            include_always_on: bool = True) -> list[Item]:
    items = [Item(str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p),
                  estimate_tokens(read(p), classify(p)), classify(p)) for p in paths]
    if include_always_on:
        items = always_on(paths) + items + tool_schemas()
    if prompt is not None:
        items.append(Item(str(prompt), estimate_tokens(read(prompt), "prompt"), "prompt"))
    return items


def total(items: list[Item]) -> int:
    return sum(i.tokens for i in items)


def mix(items: list[Item]) -> dict[str, float]:
    grand = total(items) or 1
    out: dict[str, float] = {}
    for item in items:
        out[item.kind] = out.get(item.kind, 0.0) + item.tokens / grand
    return out


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
FOOTER = """
  ---------------------------------------------------------------------------
  ctxmeter is an ESTIMATOR, not a tokenizer. See tools/calibration.md for its
  measured error against a real tokenizer on this repository's file types.
  Vendors' own tokenizers differ from each other by a similar margin.
  It counts only what you listed. The hidden system prompt, the editor's
  retrieval and anything the agent chooses to read are invisible to it, so
  every number here is a FLOOR. Use deltas. A token is not a credit."""


def show(items: list[Item], heading: str) -> None:
    print(heading)
    print("  %-46s %9s  %s" % ("what", "est. tok", "kind"))
    for item in sorted(items, key=lambda i: -i.tokens):
        share = 100.0 * item.tokens / (total(items) or 1)
        note = f"  ({item.note})" if item.note else ""
        print("  %-46s %9d  %-12s %4.1f%%%s"
              % (item.label[:46], item.tokens, item.kind, share, note))
    print("  %-46s %9d" % ("TOTAL", total(items)))


def mixed_badly(before: list[Item], after: list[Item]) -> str | None:
    """Is a single percentage honest across these two bundles?

    If the cut removed a different KIND of content than it kept - dense JSON
    against loose prose - the estimator's error no longer cancels between the two
    numbers, and a headline percentage is not supportable.
    """
    a, b = mix(before), mix(after)
    for kind in set(a) | set(b):
        if abs(a.get(kind, 0.0) - b.get(kind, 0.0)) > 0.25:
            return kind
    return None


def cmd_diff(args) -> int:
    before = measure(load_bundle(Path(args.before)))
    after = measure(load_bundle(Path(args.after)))
    show(before, f"\nBEFORE  {args.before}")
    show(after, f"\nAFTER   {args.after}")

    saved = total(before) - total(after)
    print(f"\n  saved {saved} est. tokens")
    offender = mixed_badly(before, after)
    if offender and not args.allow_mixed:
        print(f"  NOT printing a percentage: the '{offender}' share of the bundle moved")
        print("  by more than 25 points, so the estimator's error does not cancel")
        print("  between these two numbers. Re-run with --allow-mixed if you accept that.")
        print("  before mix: " + fmt_mix(mix(before)))
        print("  after  mix: " + fmt_mix(mix(after)))
    elif total(before):
        print(f"  cut {100.0 * saved / total(before):.1f}%")
        if offender:
            print("  before mix: " + fmt_mix(mix(before)))
            print("  after  mix: " + fmt_mix(mix(after)))
    if args.rate:
        print(f"  what-if at the rate you supplied ({args.rate} per 1M input): "
              f"{saved / 1_000_000 * args.rate:.4f} saved per turn, uncached")
    print(FOOTER)
    return 0


def fmt_mix(m: dict[str, float]) -> str:
    return ", ".join(f"{k} {100*v:.0f}%" for k, v in sorted(m.items(), key=lambda kv: -kv[1]))


def cmd_count(args) -> int:
    if not args.absolute:
        print("ctxmeter: counting one bundle gives an ABSOLUTE number, and absolute")
        print("  numbers from an estimator get screenshotted into decks as fact.")
        print("  Pass --absolute if you mean it, or use `diff` to compare two bundles.")
        return 2
    paths = [Path(p) if Path(p).is_absolute() else REPO / p for p in args.paths]
    items = measure([p for p in paths if p.is_file()],
                    prompt=Path(args.prompt) if args.prompt else None)
    show(items, "\nBUNDLE")
    print(FOOTER)
    return 0


def cmd_repo(args) -> int:
    if not args.absolute:
        print("ctxmeter: pass --absolute. See `count` for why.")
        return 2
    paths = [p for p in sorted(REPO.rglob("*"))
             if p.is_file() and ".git" not in p.parts and p.suffix in
             {".py", ".json", ".md", ".txt", ".toml", ".cfg"}]
    items = measure(paths)
    show(items, "\nWHOLE REPOSITORY  (what 'attach everything' costs you)")
    print(FOOTER)
    return 0


def cmd_turns(args) -> int:
    """History is a prefix that is re-sent in full, every turn."""
    items = measure(load_bundle(Path(args.bundle)))
    standing = total(items)
    per_turn_reply = args.reply
    print(f"\n  standing context: {standing} est. tokens, re-sent every turn")
    print("  %5s %14s %14s" % ("turn", "sent", "cumulative"))
    cumulative = 0
    for turn in range(1, args.turns + 1):
        sent = standing + per_turn_reply * (turn - 1) * 2
        cumulative += sent
        print("  %5d %14d %14d" % (turn, sent, cumulative))
    print(f"\n  {args.turns} turns cost about {cumulative} est. input tokens to send"
          f" {per_turn_reply * args.turns} tokens of answer.")
    if cumulative:
        print(f"  That is {cumulative / max(per_turn_reply * args.turns, 1):.0f}"
              " input tokens per output token.")
    print(FOOTER)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ctxmeter", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rate", type=float,
                        help="price per 1M input tokens, for a what-if line. "
                             "There is no default on purpose.")
    sub = parser.add_subparsers(dest="command")

    p_diff = sub.add_parser("diff", help="compare two bundles (start here)")
    p_diff.add_argument("before")
    p_diff.add_argument("after")
    p_diff.add_argument("--allow-mixed", action="store_true")
    p_diff.set_defaults(func=cmd_diff)

    p_count = sub.add_parser("count", help="itemise one bundle")
    p_count.add_argument("paths", nargs="+")
    p_count.add_argument("--absolute", action="store_true")
    p_count.add_argument("--prompt")
    p_count.set_defaults(func=cmd_count)

    p_repo = sub.add_parser("repo", help="what attaching the whole repository costs")
    p_repo.add_argument("--absolute", action="store_true")
    p_repo.set_defaults(func=cmd_repo)

    p_turns = sub.add_parser("turns", help="how a conversation grows")
    p_turns.add_argument("bundle")
    p_turns.add_argument("--turns", type=int, default=6)
    p_turns.add_argument("--reply", type=int, default=250,
                         help="estimated tokens in each answer")
    p_turns.set_defaults(func=cmd_turns)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
