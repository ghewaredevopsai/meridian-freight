"""The depot manifest.

A manifest is the paper that travels with the freight: one line per consignment,
with the weight the driver should see and the amount the depot should collect.

Added in a hurry when the Guwahati depot went live and needed a printable sheet
before the quote service was reachable from their network.
"""

from datetime import datetime

from . import tariffs
from .models import Consignment

MANIFEST_COLUMNS = ("consignment", "pieces", "weight_g", "destination", "amount_minor")


def manifest_total_minor(consignment: Consignment, tariff: dict | None = None) -> int:
    """What the depot collects for this consignment.

    Same arithmetic as the quote: band price for the chargeable weight, the piece
    and dangerous-goods surcharges, then fuel.
    """
    tariff = tariff or tariffs.load()
    zone = tariffs.zone_of(tariff, consignment.shipper.depot,
                           consignment.consignee.depot)
    band_list = tariffs.bands(tariff, consignment.scope.value,
                              consignment.service.value, zone)

    divisor = tariffs.dim_divisor(tariff, consignment.scope.value)
    dimensional_g = (consignment.volume_cm3 * 1000) // divisor
    weight_g = max(consignment.actual_weight_g, dimensional_g)

    base = 0
    if weight_g <= 1000:
        base = band_list[0]["minor"]
    else:
        for band in band_list:
            limit = band.get("up_to_g")
            if limit is None:
                base = (weight_g * band["per_kg_minor"]) // 1000
                break
            if weight_g < limit:
                base = band["minor"]
                break

    pct = tariffs.fuel_pct(tariff, consignment.booked_at)
    fuel = (base * int(pct * 100)) // 10_000

    extras = tariffs.surcharge(tariff, "HANDLING")["per_piece_minor"] * consignment.piece_count
    if consignment.dangerous_goods:
        extras += tariffs.surcharge(tariff, "DG")["flat_minor"]
    remote = tariffs.surcharge(tariff, "REMOTE")
    if consignment.consignee.depot in remote["depots"]:
        extras += remote["flat_minor"]

    return base + fuel + extras


def manifest_line(consignment: Consignment, tariff: dict | None = None) -> dict:
    return {
        "consignment": consignment.id,
        "pieces": consignment.piece_count,
        "weight_g": consignment.actual_weight_g,
        "destination": consignment.consignee.depot,
        "amount_minor": manifest_total_minor(consignment, tariff),
    }


def build(consignments: list[Consignment], depot: str,
          tariff: dict | None = None) -> dict:
    """Everything leaving one depot, in booking order."""
    tariff = tariff or tariffs.load()
    outbound = [c for c in consignments if c.shipper.depot == depot]
    outbound.sort(key=lambda c: c.booked_at)
    lines = [manifest_line(c, tariff) for c in outbound]
    return {
        "depot": depot,
        "lines": lines,
        "piece_total": sum(line["pieces"] for line in lines),
        "amount_total_minor": sum(line["amount_minor"] for line in lines),
    }


def as_text(manifest: dict, printed_at: datetime) -> str:
    """The printable sheet. Fixed width, because the depot printers are."""
    head = f"MERIDIAN FREIGHT  manifest {manifest['depot']}  {printed_at:%Y-%m-%d %H:%M}"
    rule = "-" * len(head)
    rows = [
        "%-12s %6d %9d  %-4s %12d" % (
            line["consignment"], line["pieces"], line["weight_g"],
            line["destination"], line["amount_minor"])
        for line in manifest["lines"]
    ]
    total = "%-12s %6d %9s  %-4s %12d" % (
        "TOTAL", manifest["piece_total"], "", "", manifest["amount_total_minor"])
    return "\n".join([head, rule, *rows, rule, total])
