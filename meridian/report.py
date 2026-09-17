"""The exceptions report.

One row per consignment that raised at least one exception code, so the desk can
work the list before the night sync. Clean consignments never appear.
"""

from datetime import datetime

from . import tariffs, validate
from .models import Consignment


def exceptions(consignments: list[Consignment], tariff: dict | None = None) -> list[dict]:
    """Rows for every consignment with at least one exception, worst first.

    'Worst' means most codes; ties keep booking order, so working down the list
    is also working oldest-first within a severity.
    """
    tariff = tariff or tariffs.load()
    rows = []
    for c in consignments:
        codes = validate.check(c, tariff)
        if codes:
            rows.append({
                "consignment": c.id,
                "codes": codes,
                "reasons": [validate.describe(code) for code in codes],
                "destination": c.consignee.depot,
                "booked_at": c.booked_at,
            })
    rows.sort(key=lambda r: (-len(r["codes"]), r["booked_at"]))
    return rows


def summarise(rows: list[dict]) -> dict:
    """Counts per code, for the morning stand-up.

    Every code in the closed set appears, including the ones at zero: a code that
    drops off the report is indistinguishable from a code nobody is checking.
    """
    counts = {code: 0 for code in validate.EXCEPTION_CODES}
    for row in rows:
        for code in row["codes"]:
            counts[code] += 1
    return {
        "total_consignments_with_exceptions": len(rows),
        "counts": counts,
    }


def as_text(rows: list[dict], printed_at: datetime) -> str:
    if not rows:
        return f"MERIDIAN FREIGHT  exceptions  {printed_at:%Y-%m-%d %H:%M}\nNothing to work."
    head = f"MERIDIAN FREIGHT  exceptions  {printed_at:%Y-%m-%d %H:%M}"
    lines = [head, "-" * len(head)]
    for row in rows:
        lines.append("%-12s %-4s %s" % (row["consignment"], row["destination"],
                                        ", ".join(row["codes"])))
        for reason in row["reasons"]:
            lines.append(" " * 18 + reason)
    return "\n".join(lines)
