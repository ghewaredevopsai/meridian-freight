"""Pricing a consignment.

This module is the only place that decides what a consignment costs. If you find
yourself adding up charges anywhere else, call `quote()` instead.

Money is integer minor units throughout. No float ever holds an amount.
"""

from datetime import datetime

from . import tariffs
from .errors import RatingError
from .models import Charge, Consignment, Quote, Scope

OVERSIZE_DIMENSION_CM = 120
OVERSIZE_VOLUME_CM3 = 250_000


def chargeable_weight_g(consignment: Consignment, tariff: dict) -> int:
    """The greater of actual weight and dimensional weight.

    Dimensional weight divides volume by the divisor for the scope: they are not
    the same number for domestic and export, and using the wrong one is the
    commonest pricing complaint we get.
    """
    divisor = tariffs.dim_divisor(tariff, consignment.scope.value)
    dimensional_g = (consignment.volume_cm3 * 1000) // divisor
    return max(consignment.actual_weight_g, dimensional_g)


def _band_amount(band_list: list[dict], weight_g: int) -> int:
    """Price for a weight against a zone's band table.

    Bands are half-open: a band that reads `up_to_g: 2000` covers weights from the
    previous band's limit up to but NOT including 2000 g. A parcel of exactly
    2000 g is priced in the next band up.
    """
    # 1 kg is the commonest parcel by a distance - short-circuit it rather than
    # walking the whole table every time.
    if weight_g <= 1000:
        return band_list[0]["minor"]

    for band in band_list:
        limit = band.get("up_to_g")
        if limit is None:
            per_kg = band["per_kg_minor"]
            return (weight_g * per_kg) // 1000
        if weight_g < limit:
            return band["minor"]
    raise RatingError(f"no band covers {weight_g} g")


def _surcharges(consignment: Consignment, tariff: dict) -> list[Charge]:
    out: list[Charge] = []

    handling = tariffs.surcharge(tariff, "HANDLING")
    out.append(Charge("HANDLING", handling["label"],
                      handling["per_piece_minor"] * consignment.piece_count))

    if any(max(p.length_cm, p.width_cm, p.height_cm) > OVERSIZE_DIMENSION_CM
           or p.volume_cm3 > OVERSIZE_VOLUME_CM3 for p in consignment.parcels):
        over = tariffs.surcharge(tariff, "OVERSIZE")
        out.append(Charge("OVERSIZE", over["label"], over["flat_minor"]))

    if consignment.dangerous_goods:
        dg = tariffs.surcharge(tariff, "DG")
        out.append(Charge("DG", dg["label"], dg["flat_minor"]))

    remote = tariffs.surcharge(tariff, "REMOTE")
    if consignment.consignee.depot in remote["depots"]:
        out.append(Charge("REMOTE", remote["label"], remote["flat_minor"]))

    if consignment.declared_value_minor > 0:
        ins = tariffs.surcharge(tariff, "INSURANCE")
        pct = ins["pct_of_declared"]
        amount = (consignment.declared_value_minor * round(pct * 100)) // 10_000
        out.append(Charge("INSURANCE", ins["label"], max(amount, ins["minimum_minor"])))

    return out


def quote(consignment: Consignment, tariff: dict | None = None) -> Quote:
    """Price a consignment.

    Order matters: base, then surcharges, then fuel on the sum of the two. Fuel is
    a percentage of what the shipment costs, and a surcharge is part of what it
    costs. Applying fuel to the base alone under-bills every shipment that carries
    one, which is most of them.
    """
    tariff = tariff or tariffs.load()
    if not consignment.parcels:
        raise RatingError(f"{consignment.id}: nothing to price - no parcels")

    origin = consignment.shipper.depot
    destination = consignment.consignee.depot
    zone = tariffs.zone_of(tariff, origin, destination)
    band_list = tariffs.bands(tariff, consignment.scope.value,
                              consignment.service.value, zone)

    weight_g = chargeable_weight_g(consignment, tariff)
    base = _band_amount(band_list, weight_g)
    charges = [Charge("BASE", f"Freight {zone} {consignment.service.value}", base)]
    charges.extend(_surcharges(consignment, tariff))

    subtotal = sum(c.amount_minor for c in charges)
    pct = tariffs.fuel_pct(tariff, consignment.booked_at)
    fuel = (subtotal * round(pct * 100)) // 10_000
    charges.append(Charge("FUEL", f"Fuel {pct}%", fuel))

    return Quote(
        consignment_id=consignment.id,
        chargeable_weight_g=weight_g,
        charges=tuple(charges),
        total_minor=subtotal + fuel,
        currency=tariff["currency"],
    )


def split_evenly(total_minor: int, parts: int) -> list[int]:
    """Split an amount across parts so the pieces add back to the total.

    Nothing is rounded: the remainder goes to the earliest parts, one minor unit
    each, so a long run of splits cannot drift above or below the totals.
    """
    if parts <= 0:
        raise RatingError("cannot split across zero parts")
    each, remainder = divmod(total_minor, parts)
    return [each + (1 if i < remainder else 0) for i in range(parts)]


def is_export(consignment: Consignment) -> bool:
    return consignment.scope is Scope.EXPORT


def rated_at(consignment: Consignment) -> datetime:
    """The date a quote is priced from. Always the booking date, never now()."""
    return consignment.booked_at
