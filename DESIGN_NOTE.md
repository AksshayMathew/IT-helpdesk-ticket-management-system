# Design Note - IT Helpdesk Ticket Management System

**Employee ID used:** 56040183 (typed in when the program starts)

## Our personalised parameters

| Parameter | Value |
|---|---|
| Ticket categories | Hardware, VPN, Application Bug, Account Lockout, Access Request |
| SLA hours | Critical = 4, High = 6, Medium = 47, Low = 108 |
| Ticket ID prefix | `SR` (tickets look like `SR-0001`) |

These come from `get_my_parameters("56040183")` in `personalize.py`, called with the
ID the user types at the start. The function always returns the same result for the
same ID, so the program behaves the same every time. Each employee ID has its own
tickets file (`tickets_<id>.json`), so different IDs never mix their tickets.

## How the program is built

We split the code into small files so each one does one job. `models.py`
holds the `Ticket` class, `storage.py` reads and writes the JSON file,
`helpdesk.py` has the rules (validation, status flow, SLA, summary, filter)
and `main.py` only deals with the menu and typing. Because the rules are not
mixed with `input()` and `print()`, we could write unit tests for them
easily.

## One design decision and why

**Decision:** the allowed status changes are stored as a dictionary that maps each
status to the statuses it may move to next:

```python
STATUS_TRANSITIONS = {
    "Open": ("In Progress",),
    "In Progress": ("Resolved",),
    "Resolved": ("Closed", "Open"),
    "Closed": (),
}
```

**Why:** we first stored the flow as an ordered tuple, where a ticket could only
move to the status right after its current one. That only allows a straight line,
so a Resolved ticket could never be reopened. With the dictionary, the rule for any
status is just a lookup, so a status can have more than one allowed next step
(Resolved can go to Closed or back to Open) and Closed has none. A bad move like
Open -> Closed is still rejected by one check, and the error message lists every
allowed status. If the team ever adds a status or a new move, only this dictionary
changes. The alternative, a long if/elif chain for every pair of statuses, is easy
to get wrong and hard to change.

**Related choices:** a ticket counts as SLA-breached only while it is not
Resolved or Closed, using `created_at + timedelta(hours=sla)` compared with
the current time. The next ticket number is the highest number already used
plus one, so IDs stay unique after the program is restarted. A reopened ticket keeps its
original creation time, so its SLA is still measured from then and it can be flagged as
breached again straight away.
