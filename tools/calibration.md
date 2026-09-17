# ctxmeter calibration

`ctxmeter` is an estimator. This file is the measurement that earns it the right to
be taught with, and the reason its constants are the numbers they are.

**Measured 18 September 2026** against `tiktoken`'s `o200k_base` and `cl100k_base`,
over every `.py`, `.json`, `.md` and `.txt` file in this repository at that date.

## Result

| Content class | Files | Mean error | Worst under | Worst over |
|---|--:|--:|--:|--:|
| code (`.py`) | 16 | **+0.3%** | &minus;6.8% | +15.4% |
| data (`.json`) | 2 | **&minus;0.4%** | &minus;3.8% | +3.0% |
| prose (`.md`, `.txt`) | 3 | **&minus;0.8%** | &minus;2.4% | 0.0% |
| **Whole repository** | 21 | **+0.1%** | | |

**Read it as: reliable in aggregate, and worth about &plusmn;15% on any single code
file.** Which is the same thing as saying: use it for bundles and for deltas, not to
pronounce on one file.

## The number that puts the rest in perspective

The two reference tokenizers **disagree with each other by 0.1%** on this repository
in total &mdash; but that is a coincidence of this corpus, not a rule. Across the wider
world they differ by margins comparable to this estimator's own error, and neither is
"correct" for a model you do not control. There is no ground truth available to a
participant on a corporate laptop. That is the honest case for measuring your own
deltas with one consistent instrument rather than chasing someone else's absolute.

## What was fitted

A grid search over the four constants in `ctxmeter.py`, minimising mean absolute
per-file error:

| Constant | Value | Meaning |
|---|--:|---|
| `LONG_PIECE` | 8 | pieces longer than this get split by a real tokenizer |
| `CHARS_PER_SUBWORD` | 6 | ...into roughly this many characters each |
| `WHITESPACE_RUN` | 12 | a run of blanks costs about one token per this many |
| `PUNCTUATION_RUN` | 3 | so does a run of brackets, quotes and commas |

Then a residual per-class factor, because code still read high after fitting &mdash;
identifiers split more than their length predicts:

```python
CALIBRATION = {"code": 0.86, "data": 0.95, "prose": 0.94, ...}
```

Before fitting, the estimator over-counted by **+26%** overall (+32.5% on code). The
first draft used the familiar characters&divide;4 rule and was worse still. Neither would
have been dishonest to use for a *ratio* &mdash; the bias largely cancels between a
before and an after &mdash; but both would have been indefensible the moment somebody
read an absolute out loud.

## Re-running it

`ctxmeter` itself must stay standard-library only, so the reference tokenizer is
installed **outside** this repository, used once, and thrown away:

```bash
python3 -m venv /tmp/tkvenv
/tmp/tkvenv/bin/pip install tiktoken
/tmp/tkvenv/bin/python - <<'PY'
import sys, statistics; sys.path.insert(0, "tools")
import tiktoken
from ctxmeter import estimate_tokens, classify, REPO
enc = tiktoken.get_encoding("o200k_base")
for p in sorted(REPO.rglob("*")):
    if p.is_file() and p.suffix in {".py", ".json", ".md", ".txt"}:
        t = p.read_text(encoding="utf-8", errors="replace")
        if t.strip():
            e, r = estimate_tokens(t, classify(p)), len(enc.encode(t))
            print("%-34s %+6.1f%%" % (p, 100.0 * (e - r) / r))
PY
```

**Re-run this after any large change to the repository**, and update the table above
with the date. A calibration nobody re-ran is a claim, not a measurement.

## What it still cannot see

None of the above touches the largest source of error in practice, which is not the
arithmetic:

- the vendor's hidden system prompt
- the editor's own retrieval and repository indexing
- whatever the agent decides to open once it starts working
- the exact serialisation of tool and function schemas

Every number `ctxmeter` prints is a **floor**. The calibration above tells you how
good the arithmetic is on the text you listed. It tells you nothing about what else
went with it.
