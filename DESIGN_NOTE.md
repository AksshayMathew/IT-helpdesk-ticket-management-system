# Design Note - IT Helpdesk Ticket Management System

**Employee ID used:** 56040183

## Our personalised parameters

| Parameter | Value |
|---|---|
| Ticket categories | Hardware, VPN, Application Bug, Account Lockout, Access Request |
| SLA hours | Critical = 4, High = 6, Medium = 47, Low = 108 |
| Ticket ID prefix | `SR` (tickets look like `SR-0001`) |

These come from `get_my_parameters("56040183")` in `personalize.py`. The
function always returns the same result for the same ID, so the program
behaves the same every time we run it.

## How the program is built

We split the code into small files so each one does one job. `models.py`
holds the `Ticket` class, `storage.py` reads and writes the JSON file,
`helpdesk.py` has the rules (validation, status flow, SLA, summary, filter)
and `main.py` only deals with the menu and typing. Because the rules are not
mixed with `input()` and `print()`, we could write unit tests for them
easily.

## One design decision and why

**Decision:** the allowed status changes are stored as an ordered tuple,
`STATUS_FLOW = ("Open", "In Progress", "Resolved", "Closed")`, and a ticket
may only move to the status that comes *right after* its current one.

**Why:** the first idea was a long if/elif chain for every allowed pair of
statuses, which is easy to get wrong and hard to change. With the tuple, the
rule is just "find the current position, the next one is the only allowed
move", so a jump like Open -> Closed is rejected by one check and the error
message can tell the user exactly which status is allowed next. If the team
ever adds a new status, only the tuple needs to change.

**Related choices:** a ticket counts as SLA-breached only while it is not
Resolved or Closed, using `created_at + timedelta(hours=sla)` compared with
the current time. The next ticket number is the highest number already used
plus one, so IDs stay unique after the program is restarted.
