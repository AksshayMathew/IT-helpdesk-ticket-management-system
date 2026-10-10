# IT Helpdesk Ticket Management System (CLI)

A command-line helpdesk tool to log, track, update and resolve IT support
tickets, with SLA breach detection. Pure Python 3, standard library only.

## How to run

```
python main.py
```

Tickets are saved to `tickets.json` (created automatically in this folder)
after every change and loaded again on the next start.

To run the tests:

```
python -m unittest -v
```

To print our personalised parameters (categories, SLA hours, ID prefix):

```
python personalize.py
```

## Menu options

| Option | What it does |
|---|---|
| 1 | Raise a ticket (category, priority, requester, description) - ID and timestamp are automatic, e.g. `SR-0001` |
| 2 | Update status: Open -> In Progress -> Resolved -> Closed (jumps are rejected) |
| 3 | List all tickets (SLA-breached ones are flagged) |
| 4 | Filter / search by category, priority and/or status |
| 5 | Summary: counts by status, counts by category, SLA-breached tickets |
| 6 | Backdate a ticket - a demo helper so an SLA breach can be shown quickly |
| 0 | Exit |

Invalid input never crashes the program: it prints a clear error and asks again.

## Project layout

| File | Purpose |
|---|---|
| `personalize.py` | Parameters generated from our employee ID (categories, SLA hours, prefix) |
| `models.py` | `Ticket` class, priorities, status flow, custom `InvalidTicketError` |
| `storage.py` | Saving and loading tickets as JSON |
| `helpdesk.py` | Business logic: raise, validate, update status, SLA, summary, filter |
| `main.py` | The interactive menu |
| `test_helpdesk.py` | Unit tests |
| `DESIGN_NOTE.md` | One-page design note |

## Our parameters (employee ID 56040183)

- Categories: Hardware, VPN, Application Bug, Account Lockout, Access Request
- SLA hours: Critical 4, High 6, Medium 47, Low 108
- Ticket prefix: `SR`
