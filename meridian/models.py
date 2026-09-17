"""Domain types for the Meridian freight desk.

Money is an integer number of minor units (paise, cents) everywhere in this package.
Nothing here holds a float. The only place a decimal string appears is the CLI, and
only on the way out.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Service(str, Enum):
    """Service level. The value is what appears in a manifest file."""

    ECONOMY = "economy"
    STANDARD = "standard"
    EXPRESS = "express"


class Scope(str, Enum):
    """Domestic and export price differently and measure volume differently."""

    DOMESTIC = "domestic"
    EXPORT = "export"


@dataclass(frozen=True)
class Party:
    name: str
    depot: str
    country: str = "IN"


@dataclass(frozen=True)
class Parcel:
    """One physical piece. Dimensions are centimetres, weight is grams."""

    length_cm: int
    width_cm: int
    height_cm: int
    weight_g: int

    @property
    def volume_cm3(self) -> int:
        return self.length_cm * self.width_cm * self.height_cm


@dataclass(frozen=True)
class Leg:
    """One movement between two depots.

    A consignment may have no legs at all: it has been booked and priced but not
    yet routed. That is a valid state, not an error.
    """

    from_depot: str
    to_depot: str
    depart: datetime
    arrive: datetime
    carrier: str


@dataclass
class Consignment:
    id: str
    shipper: Party
    consignee: Party
    parcels: list[Parcel]
    service: Service
    scope: Scope
    booked_at: datetime
    legs: list[Leg] = field(default_factory=list)
    declared_value_minor: int = 0
    dangerous_goods: bool = False

    @property
    def actual_weight_g(self) -> int:
        return sum(p.weight_g for p in self.parcels)

    @property
    def volume_cm3(self) -> int:
        return sum(p.volume_cm3 for p in self.parcels)

    @property
    def piece_count(self) -> int:
        return len(self.parcels)


@dataclass(frozen=True)
class Charge:
    """One line on a quote. Positive amounts only; discounts are not modelled."""

    code: str
    label: str
    amount_minor: int


@dataclass(frozen=True)
class Quote:
    """The result of rating a consignment.

    Public functions in this package return this, never a dict. The CLI is the
    only place that serialises it.
    """

    consignment_id: str
    chargeable_weight_g: int
    charges: tuple[Charge, ...]
    total_minor: int
    currency: str = "INR"

    def charge(self, code: str) -> Charge | None:
        for c in self.charges:
            if c.code == code:
                return c
        return None
