# Freight desk runbook

Written for whoever is on the desk. It is not a specification and it has never been
tidied: sections were added the week something went wrong, which is why the order
makes no sense and the important parts are in the middle of paragraphs.

Everything below is true of the code in `meridian/`. Where this document and
`docs/tariff-2026-notes.md` disagree, **this document is right** &mdash; the notes
file was written against the 2025 tariff and nobody has deleted it.

---

## Opening the day

Pull the overnight file, run the exceptions report, work the list top down. The
report is sorted worst-first by number of exception codes, and within the same
count it keeps booking order, so working down the list is also working oldest-first.

```
python3 -m meridian exceptions
```

A consignment with **no legs is not an error**. It has been booked and priced but
not routed yet, which is the ordinary state of anything that came in after the lane
cutoff. It only becomes an exception (MF-03) if it was booked *before* the cutoff
and is still sitting there, because that means somebody forgot it. People new to
the desk "fix" unrouted consignments constantly and it is always wrong.

## Money

Every amount in the system is an **integer number of paise**. A percentage &mdash;
fuel, insurance &mdash; is applied in basis points and floored to the whole paisa,
once, in `rating.quote()`. The only other division is splitting a total across
pieces, and `split_evenly()` does that, guaranteeing the pieces add back to the
original.

That function does not round at all. It hands the remainder out one paisa at a time
to the first pieces. Rounding each piece on its own instead &mdash; half up, half to
even, any rule &mdash; drifts the depot's takings away from the invoiced total by a
few hundred rupees a quarter, and reconciliation then has to find it.

Never put an amount in a float. Not to display it, not "just for the report", not
temporarily. The only place a decimal point appears is `cli.money()`, on the way to
the screen.

## Weight

Two weights matter and they are not the same number.

**Actual weight** is what the scale says. **Dimensional weight** is volume divided
by a divisor, and the divisor depends on where the freight is going:

- domestic: **5000**
- export: **6000**

You charge on whichever is larger. Getting the divisor the wrong way round is the
single most common pricing complaint we receive, because export freight is usually
the bulky kind and the error always favours us, which customers notice.

Weight bands are **half-open**. A band that reads `up_to_g: 2000` covers everything
from the band below it up to but *not including* 2000 g. A parcel of exactly 2000 g
prices in the next band up. Ask anyone who has argued with a customer about a
2.000 kg parcel why this is written down.

## Saturday collections

A consignment collected on a Saturday carries a flat **Saturday collection**
surcharge, code `SAT`, of 32000 paise. Flat, not a percentage &mdash; the driver
costs the same whatever is in the box.

It is a surcharge like any other, so it goes in **before** fuel.

**Export is excluded.** We do not collect export freight on Saturdays at all, so a
Saturday export booking is a data error rather than a chargeable collection, and it
must not pick up the surcharge.

A consignment is a Saturday collection when `booked_at` falls on a Saturday. As
everywhere else, that is the booking's own timestamp &mdash; not today.

## Charging order

Base rate, then surcharges, then fuel **on the sum of the two**.

Fuel is a percentage of what the shipment costs, and a surcharge is part of what it
costs. Applying fuel to the base alone under-bills every consignment carrying a
surcharge, which is nearly all of them. It is a small error per consignment and a
large one per month.

The fuel percentage is read **for the month the consignment was booked**, never for
today. The nightly rerun prices yesterday's bookings and has to arrive at
yesterday's answer.

## Clocks

Every cutoff is a wall-clock time at the **origin depot**, and every timestamp in
the system is naive local time at the depot it belongs to. We do not store
timezones. A manifest that crosses two depots carries both times as written, and
nobody converts.

Nothing in the package calls `datetime.now()`. The clock arrives as an argument
&mdash; `--today` on the command line, `booked_at` on a consignment. This is not
fussiness: the nightly rerun, the tests and the depot reprints all need to ask "what
was true at this moment", and a function that reads the wall clock cannot answer.

## Exception codes

There are six. There have been six since the desk opened.

| Code | Meaning |
|---|---|
| MF-01 | Missing or zero dimensions on at least one piece |
| MF-02 | Declared value above the cover ceiling |
| MF-03 | Booked before the lane cutoff but still unrouted |
| MF-04 | Dangerous goods without a signed declaration |
| MF-05 | Manifest weight disagrees with the sum of the pieces |
| MF-06 | Booking date outside the tariff's effective range |

The downstream billing feed rejects any code it does not recognise, and a rejected
batch is a morning of somebody's life. A new code is a conversation with the billing
team, not a new string typed at a call site. They live in `meridian/validate.py`.

## Tariff dates

`effective_from` and `effective_to` are **both inclusive**. A booking made on 31
December is priced on that year's tariff. This catches people out every January.

## Routing

Express goes direct or it does not go. Everything else on a long lane routes through
a hub, and we allow two hours on the ground to sort and reload.

`route()` returns the legs, it does not attach them. When a lane is suspended the
desk re-routes the same consignment against a different tariff and compares, and a
function that quietly appended to the consignment would have made that a bug rather
than a comparison.

## Things that are not our problem

Rate negotiation, credit control, customs paperwork, and anything a customer emails
about a shipment that is already delivered. Forward and move on.
