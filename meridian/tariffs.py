"""Loading and indexing the tariff table.

The tariff is data, not code. It is reissued every year and the file is large, so
nothing in this module holds more of it in memory than it needs.
"""

import json
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from .errors import TariffError

DEFAULT_TARIFF = Path(__file__).resolve().parent.parent / "data" / "tariff.json"


@lru_cache(maxsize=4)
def load(path: str | None = None) -> dict:
    """Read a tariff file. Cached: the same path is parsed once per process."""
    p = Path(path) if path else DEFAULT_TARIFF
    if not p.exists():
        raise TariffError(f"no tariff at {p}")
    with p.open(encoding="utf-8") as fh:
        return json.load(fh)


def lane(tariff: dict, from_depot: str, to_depot: str) -> dict:
    for ln in tariff["lanes"]:
        if ln["from"] == from_depot and ln["to"] == to_depot:
            return ln
    raise TariffError(f"no lane {from_depot}->{to_depot}")


def zone_of(tariff: dict, from_depot: str, to_depot: str) -> str:
    return lane(tariff, from_depot, to_depot)["zone"]


def bands(tariff: dict, scope: str, service: str, zone: str) -> list[dict]:
    try:
        return tariff["rates"][scope][service]["zones"][zone]
    except KeyError as exc:
        raise TariffError(f"no rates for {scope}/{service}/{zone}") from exc


def dim_divisor(tariff: dict, scope: str) -> int:
    return tariff["dim_divisor"][scope]


def fuel_pct(tariff: dict, when: datetime) -> float:
    """The fuel percentage in force for the month of `when`.

    There is no 'current' fuel percentage. It is always read for a date, and the
    date is the booking date, not today.
    """
    key = when.strftime("%Y-%m")
    table = tariff["fuel_pct_by_month"]
    if key not in table:
        raise TariffError(f"no fuel percentage for {key}")
    return table[key]


def surcharge(tariff: dict, code: str) -> dict:
    try:
        return tariff["surcharges"][code]
    except KeyError as exc:
        raise TariffError(f"unknown surcharge {code}") from exc
