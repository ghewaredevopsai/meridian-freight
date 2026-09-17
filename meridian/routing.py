"""Choosing legs for a consignment.

Routing is separate from pricing on purpose: a consignment can be priced the
moment it is booked, and routed later - or never, if it is cancelled. Nothing in
this module may import `rating`.
"""

from datetime import datetime, timedelta

from . import tariffs
from .errors import RoutingError
from .models import Consignment, Leg, Service

#: Depots we will route a long leg through, in preference order.
HUBS = ("DEL", "BOM", "BLR")

#: Express never goes through a hub: it flies direct or it does not go.
DIRECT_ONLY = (Service.EXPRESS,)


def cutoff_for(consignment: Consignment, tariff: dict | None = None) -> datetime:
    """The wall-clock moment, at the origin depot, after which this books tomorrow.

    Naive local time at the origin. We do not store or convert timezones anywhere
    in this package: every depot's clock is its own, and a manifest crossing two
    depots carries both times as written.
    """
    tariff = tariff or tariffs.load()
    lane = tariffs.lane(tariff, consignment.shipper.depot, consignment.consignee.depot)
    hour, minute = (int(x) for x in lane["cutoff_local"].split(":"))
    return consignment.booked_at.replace(hour=hour, minute=minute,
                                         second=0, microsecond=0)


def route(consignment: Consignment, tariff: dict | None = None) -> list[Leg]:
    """Build the legs for a consignment.

    Returns a list, which the caller assigns. It does not mutate the consignment:
    routing twice with different tariffs is a thing the desk does when a lane is
    suspended, and a function that quietly appended would make that a bug.
    """
    tariff = tariff or tariffs.load()
    origin = consignment.shipper.depot
    destination = consignment.consignee.depot
    if origin == destination:
        raise RoutingError(f"{consignment.id}: origin and destination are both {origin}")

    lane = tariffs.lane(tariff, origin, destination)
    depart = _first_departure(consignment, tariff)

    if consignment.service in DIRECT_ONLY or lane["zone"] in ("Z1", "Z2"):
        return [_leg(origin, destination, depart, lane)]

    hub = _hub_for(origin, destination)
    if hub is None:
        return [_leg(origin, destination, depart, lane)]

    first = tariffs.lane(tariff, origin, hub)
    second = tariffs.lane(tariff, hub, destination)
    leg_one = _leg(origin, hub, depart, first)
    # Two hours on the ground to sort and reload.
    leg_two = _leg(hub, destination, leg_one.arrive + timedelta(hours=2), second)
    return [leg_one, leg_two]


def transit_hours(legs: list[Leg]) -> int:
    """Total door-to-door hours across the legs, including time on the ground."""
    if not legs:
        return 0
    return int((legs[-1].arrive - legs[0].depart).total_seconds() // 3600)


def _leg(from_depot: str, to_depot: str, depart: datetime, lane: dict) -> Leg:
    return Leg(
        from_depot=from_depot,
        to_depot=to_depot,
        depart=depart,
        arrive=depart + timedelta(hours=lane["transit_hours"]),
        carrier=lane["carrier"],
    )


def _first_departure(consignment: Consignment, tariff: dict) -> datetime:
    """Booked before the cutoff leaves today; after it, tomorrow morning."""
    cutoff = cutoff_for(consignment, tariff)
    if consignment.booked_at <= cutoff:
        return cutoff
    tomorrow = consignment.booked_at + timedelta(days=1)
    return tomorrow.replace(hour=6, minute=0, second=0, microsecond=0)


def _hub_for(origin: str, destination: str) -> str | None:
    for hub in HUBS:
        if hub not in (origin, destination):
            return hub
    return None
