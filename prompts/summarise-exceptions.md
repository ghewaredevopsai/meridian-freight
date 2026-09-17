# Daily exceptions summary

Pasted into chat every morning, with the output of `python3 -m meridian exceptions`
underneath it.

---

You are helping the freight desk work its morning exception list.

Read the exceptions report below and produce a summary for the duty supervisor.
Group the consignments by what is wrong with them, say how many of each there are,
and suggest what to do about each group. Keep it brief.

Return JSON with a `generated_for` date, an `exceptions` array and a `total`. Each
entry needs the consignment id, its codes, and a one-line action.
