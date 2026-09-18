# Meridian Freight Desk

An internal service for the freight desk: price a consignment, route it, print the
depot manifest, and list the ones needing attention before the night sync.

Python 3.11+. **Standard library only** &mdash; nothing to install, and it runs with
no network.

```bash
python3 -m unittest discover -s tests -t .     # 28 tests
python3 -m meridian quote MF-1004
python3 -m meridian route MF-1004
python3 -m meridian exceptions
python3 -m meridian manifest BOM --today 2026-03-04T09:00:00
```

## Layout

```
meridian/
  models.py      Consignment, Parcel, Leg, Quote, Charge
  rating.py      what a consignment costs - the only place that decides
  routing.py     which legs it moves on
  tariffs.py     loading and indexing data/tariff.json
  validate.py    the six exception codes, and the checks that raise them
  manifest.py    the printable depot sheet
  report.py      the exceptions report
  store.py       reading and writing consignments as JSON
  cli.py         the command line - the only module that prints
data/
  tariff.json         rates, lanes, fuel by month, surcharges
  consignments.json   40 sample consignments
docs/
  ops-runbook.md          how the desk actually works
  tariff-2026-notes.md    working notes from the tariff load
tools/
  ctxmeter.py         what a context bundle costs, estimated
  check_contract.py   does an answer have the shape we asked for
  cascade.py          cheap model first, escalate on a rule
```

## Conventions

A few things that are not obvious from the code:

- **Money is integer paise.** Nothing holds an amount in a float.
- **The clock is always injected.** Nothing calls `datetime.now()`.
- **`rating.quote()` is the only place that decides a price.**
- **`unittest`, not pytest.** There is no dependency file because there are no
  dependencies.

The rest of the desk's rules &mdash; weight divisors, band boundaries, the order
charges are applied in, what the exception codes mean &mdash; are in
[`docs/ops-runbook.md`](docs/ops-runbook.md). They have never been written down
anywhere a program can read.

## Known

- `tests/test_manifest.py` has one failing test. The manifest total and the quote
  total disagree and have for a while. Nobody has had a clear afternoon to work out
  which one is wrong.
- `scripts/nightly_sync.py` was written in an evening during the Guwahati cutover
  and has not been looked at since.

## Used by

This repository is the practice codebase for two training modules:
[Prompt &amp; Context Engineering](https://github.com/ghewaredevopsai/prompt-context-engineering)
and [Token Optimization](https://github.com/ghewaredevopsai/token-optimization).

It is **fictional**. Meridian Freight Desk is not a real company, the consignments
are generated, and the tariff is invented. Nothing here comes from any client.
