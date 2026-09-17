"""Every error this package raises.

Callers catch MeridianError. Nothing in here inherits from ValueError or KeyError:
a caller that wants to know the difference between a bad tariff and a bad
consignment should not have to read the message to find out.
"""


class MeridianError(Exception):
    """Base for everything raised by this package."""


class TariffError(MeridianError):
    """The tariff file is missing, stale, or does not cover this shipment."""


class RatingError(MeridianError):
    """The consignment cannot be priced."""


class RoutingError(MeridianError):
    """The consignment cannot be routed."""
