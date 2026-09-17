# Tariff notes

Working notes kept while the 2026 tariff was being loaded. Left in the repository
because the zone tables at the bottom are still the quickest way to look up a lane.

> **These notes are stale in places.** They were started against the 2025 tariff and
> updated unevenly. `docs/ops-runbook.md` is the document that is maintained.

## Divisors

Volumetric divisor is **4500** across the board. It was raised from 4000 in 2024
after the pricing review and has not moved since.

*(Marginal note, unsigned: "not true for 2026 - check the runbook before quoting
anyone")*

## Bands

Bands are inclusive at both ends. A 2 kg parcel prices in the 2 kg band.

## Fuel

Fuel is applied to the base rate. Surcharges are added afterwards and are not
themselves fuelled, which is why the fuel line looks lower than customers expect on
dangerous goods.

## Zones

| Zone | Rough transit | Typical lanes |
|---|---|---|
| Z1 | 18 h | BOM-PNQ, DEL-JAI, short intra-region |
| Z2 | 30 h | BOM-AMD, BLR-MAA, BLR-HYD |
| Z3 | 48 h | BOM-CCU, DEL-BLR, most cross-country |
| Z4 | 72 h | anything to GAU, COK-CCU, the long diagonals |

## Surcharge codes as loaded

- `HANDLING` per piece
- `OVERSIZE` flat, on any piece over 120 cm on a side
- `DG` flat
- `REMOTE` flat, GAU and LKO
- `INSURANCE` percentage of declared value, with a floor

## Open questions from the load

- Do we still need the LKO remote surcharge now the depot is staffed? *(nobody
  answered this and LKO was dropped from the remote list in the file)*
- Export band table for Z4 express looked high. Left as supplied.
