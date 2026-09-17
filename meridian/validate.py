"""Exception codes, and the checks that raise them.

There are six exception codes. There have been six since the desk opened, and the
downstream billing feed rejects anything it does not recognise, so a new code is a
conversation with the billing team, not a new string at a call site.

Add a code here or nowhere.
"""

from datetime import datetime

from . import tariffs
from .models import Consignment

#: The closed set. `report.py` and the billing feed both read this.
EXCEPTION_CODES: dict[str, str] = {
    "MF-01": "Missing or zero dimensions on at least one piece",
    "MF-02": "Declared value above the cover ceiling",
    "MF-03": "Booked before the lane cutoff but still unrouted",
    "MF-04": "Dangerous goods without a signed declaration",
    "MF-05": "Manifest weight disagrees with the sum of the pieces",
    "MF-06": "Booking date outside the tariff's effective range",
}

DECLARED_VALUE_CEILING_MINOR = 50_000_00


def is_known(code: str) -> bool:
    return code in EXCEPTION_CODES


def describe(code: str) -> str:
    return EXCEPTION_CODES[code]


def check(consignment: Consignment, tariff: dict | None = None,
          manifest_weight_g: int | None = None) -> list[str]:
    """Return the exception codes this consignment raises, in code order.

    An empty list means clean. A consignment with no legs is NOT an exception on
    its own: it has been booked and priced but not yet routed, which is an
    ordinary state for anything booked after the cutoff.
    """
    tariff = tariff or tariffs.load()
    found: set[str] = set()

    for parcel in consignment.parcels:
        if min(parcel.length_cm, parcel.width_cm, parcel.height_cm) <= 0:
            found.add("MF-01")

    if consignment.declared_value_minor > DECLARED_VALUE_CEILING_MINOR:
        found.add("MF-02")

    if not consignment.legs and _before_cutoff(consignment, tariff):
        found.add("MF-03")

    if consignment.dangerous_goods and not _has_declaration(consignment):
        found.add("MF-04")

    if manifest_weight_g is not None and manifest_weight_g != consignment.actual_weight_g:
        found.add("MF-05")

    if not _within_tariff(consignment.booked_at, tariff):
        found.add("MF-06")

    return sorted(found)


def _before_cutoff(consignment: Consignment, tariff: dict) -> bool:
    """Was this booked in time to have been routed the same day?

    The cutoff is a wall-clock time at the ORIGIN depot, and `booked_at` is
    already naive local time there. Nothing here converts a timezone, and nothing
    here calls datetime.now() - the clock comes in with the consignment.
    """
    try:
        lane = tariffs.lane(tariff, consignment.shipper.depot,
                            consignment.consignee.depot)
    except Exception:
        return False
    hour, minute = (int(x) for x in lane["cutoff_local"].split(":"))
    cutoff = consignment.booked_at.replace(hour=hour, minute=minute,
                                           second=0, microsecond=0)
    return consignment.booked_at <= cutoff


def _has_declaration(consignment: Consignment) -> bool:
    return consignment.declared_value_minor > 0


def _within_tariff(when: datetime, tariff: dict) -> bool:
    start = datetime.strptime(tariff["effective_from"], "%Y-%m-%d")
    end = datetime.strptime(tariff["effective_to"], "%Y-%m-%d")
    # Both ends are inclusive: a booking on 31 December is on that year's tariff.
    return start.date() <= when.date() <= end.date()
