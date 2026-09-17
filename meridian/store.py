"""Reading and writing consignments as JSON.

There is no database. The desk runs off a JSON file that the night sync rewrites,
and everything in this package takes the loaded objects, never a path.
"""

import json
from datetime import datetime
from pathlib import Path

from .errors import MeridianError
from .models import Consignment, Leg, Parcel, Party, Scope, Service

DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data" / "consignments.json"
STAMP = "%Y-%m-%dT%H:%M:%S"


def load(path: str | None = None) -> list[Consignment]:
    p = Path(path) if path else DEFAULT_DATA
    if not p.exists():
        raise MeridianError(f"no consignment file at {p}")
    with p.open(encoding="utf-8") as fh:
        raw = json.load(fh)
    return [_consignment(row) for row in raw["consignments"]]


def save(consignments: list[Consignment], path: str) -> None:
    payload = {"consignments": [_row(c) for c in consignments]}
    with Path(path).open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")


def _consignment(row: dict) -> Consignment:
    return Consignment(
        id=row["id"],
        shipper=_party(row["shipper"]),
        consignee=_party(row["consignee"]),
        parcels=[_parcel(p) for p in row["parcels"]],
        service=Service(row["service"]),
        scope=Scope(row["scope"]),
        booked_at=datetime.strptime(row["booked_at"], STAMP),
        legs=[_leg(l) for l in row.get("legs", [])],
        declared_value_minor=row.get("declared_value_minor", 0),
        dangerous_goods=row.get("dangerous_goods", False),
    )


def _party(row: dict) -> Party:
    return Party(name=row["name"], depot=row["depot"], country=row.get("country", "IN"))


def _parcel(row: dict) -> Parcel:
    return Parcel(length_cm=row["length_cm"], width_cm=row["width_cm"],
                  height_cm=row["height_cm"], weight_g=row["weight_g"])


def _leg(row: dict) -> Leg:
    return Leg(from_depot=row["from_depot"], to_depot=row["to_depot"],
               depart=datetime.strptime(row["depart"], STAMP),
               arrive=datetime.strptime(row["arrive"], STAMP),
               carrier=row["carrier"])


def _row(c: Consignment) -> dict:
    return {
        "id": c.id,
        "shipper": {"name": c.shipper.name, "depot": c.shipper.depot,
                    "country": c.shipper.country},
        "consignee": {"name": c.consignee.name, "depot": c.consignee.depot,
                      "country": c.consignee.country},
        "parcels": [{"length_cm": p.length_cm, "width_cm": p.width_cm,
                     "height_cm": p.height_cm, "weight_g": p.weight_g}
                    for p in c.parcels],
        "service": c.service.value,
        "scope": c.scope.value,
        "booked_at": c.booked_at.strftime(STAMP),
        "legs": [{"from_depot": l.from_depot, "to_depot": l.to_depot,
                  "depart": l.depart.strftime(STAMP),
                  "arrive": l.arrive.strftime(STAMP), "carrier": l.carrier}
                 for l in c.legs],
        "declared_value_minor": c.declared_value_minor,
        "dangerous_goods": c.dangerous_goods,
    }


def by_id(consignments: list[Consignment], consignment_id: str) -> Consignment:
    for c in consignments:
        if c.id == consignment_id:
            return c
    raise MeridianError(f"no consignment {consignment_id}")
