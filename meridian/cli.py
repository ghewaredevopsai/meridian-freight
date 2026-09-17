"""Command line for the freight desk.

    python3 -m meridian quote MF-1004
    python3 -m meridian manifest BOM --today 2026-03-04T09:00:00
    python3 -m meridian exceptions

This is the only module that turns minor units into something with a decimal point
in it, and the only one that prints.
"""

import argparse
from datetime import datetime

from . import manifest as manifest_mod
from . import rating, report, routing, store, tariffs
from .errors import MeridianError
from .models import Quote

STAMP = "%Y-%m-%dT%H:%M:%S"


def money(minor: int, currency: str = "INR") -> str:
    """Minor units to a printable amount. The only formatting in the package."""
    sign = "-" if minor < 0 else ""
    whole, part = divmod(abs(minor), 100)
    return f"{sign}{currency} {whole:,}.{part:02d}"


def _clock(value: str | None) -> datetime:
    """The desk's 'now'.

    Always injected, never datetime.now(): the nightly rerun prices yesterday's
    bookings and must get yesterday's answer.
    """
    if value is None:
        raise MeridianError("--today is required: this desk never reads the wall clock")
    return datetime.strptime(value, STAMP)


def print_quote(q: Quote) -> None:
    print(f"{q.consignment_id}  chargeable {q.chargeable_weight_g} g")
    for charge in q.charges:
        print("  %-10s %-28s %14s" % (charge.code, charge.label,
                                      money(charge.amount_minor, q.currency)))
    print("  %-10s %-28s %14s" % ("", "TOTAL", money(q.total_minor, q.currency)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="meridian", description=__doc__)
    parser.add_argument("--tariff", help="path to a tariff file")
    parser.add_argument("--data", help="path to a consignments file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_quote = sub.add_parser("quote", help="price one consignment")
    p_quote.add_argument("consignment_id")

    p_manifest = sub.add_parser("manifest", help="print a depot manifest")
    p_manifest.add_argument("depot")
    p_manifest.add_argument("--today", required=True)

    sub.add_parser("exceptions", help="list consignments needing attention")

    p_route = sub.add_parser("route", help="show the legs for one consignment")
    p_route.add_argument("consignment_id")

    args = parser.parse_args(argv)
    try:
        tariff = tariffs.load(args.tariff)
        consignments = store.load(args.data)

        if args.command == "quote":
            print_quote(rating.quote(store.by_id(consignments, args.consignment_id), tariff))

        elif args.command == "manifest":
            built = manifest_mod.build(consignments, args.depot, tariff)
            print(manifest_mod.as_text(built, _clock(args.today)))

        elif args.command == "exceptions":
            rows = report.exceptions(consignments, tariff)
            print(report.as_text(rows, datetime(2026, 3, 4, 9, 0, 0)))

        elif args.command == "route":
            consignment = store.by_id(consignments, args.consignment_id)
            legs = routing.route(consignment, tariff)
            for leg in legs:
                print(f"  {leg.from_depot} -> {leg.to_depot}  {leg.depart:%d %b %H:%M}"
                      f" -> {leg.arrive:%d %b %H:%M}  {leg.carrier}")
            print(f"  transit {routing.transit_hours(legs)} h")

    except MeridianError as exc:
        print(f"meridian: {exc}")
        return 2
    return 0
