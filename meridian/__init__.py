"""Meridian Freight Desk - consignment rating, routing and manifests.

A small internal service. Money is integer minor units, the clock is always
injected, and `rating.quote()` is the only place that decides what something costs.
"""

__version__ = "1.2.0"
