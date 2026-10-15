# IT Helpdesk Ticket Management System (CLI)

A command-line helpdesk tool to log, track, update and resolve IT support
tickets, with SLA breach detection. Pure Python 3, standard library only.

## How to run

```
python main.py
```

The program greets you with "Welcome to HCL Tech IT Support System" and asks for your
employee ID (letters and digits, up to 20 characters; upper and lower case are the same, so
`emp1042` is treated as `EMP1042`). The ID decides your ticket categories,
SLA hours and ticket prefix. Each employee has their own file, for example
`tickets_56040183.json` (created automatically in this folder). Tickets are saved after every
change and loaded again the next time the same ID is entered.

To run the tests:

```
python -m unittest -v
```

To print the personalised parameters (categories, SLA hours, ID prefix) for any employee ID:

```
python personalize.py
```

## Menu options

| Option | What it does |
|---|---|
| 1 | Raise a ticket (category, priority, requester, description) - ID and timestamp are automatic, e.g. `SR-0001` |
| 2 | Update status: Open -> In Progress -> Resolved -> Closed. A Resolved ticket can also be reopened (back to Open). Other moves are rejected; press Enter to cancel |
| 3 | List all tickets (SLA-breached ones are flagged) |
| 4 | Filter / search by category, priority and/or status |
| 5 | Summary: counts by status, counts by category, SLA-breached tickets |
| 6 | Backdate a ticket - a demo helper so an SLA breach can be shown quickly (press Enter to cancel) |
| 0 | Exit |

Invalid input never crashes the program: it prints a clear error and asks again.
Ctrl+C (or Ctrl+Z then Enter on Windows) exits at any prompt; saved tickets are kept.

If an employee's tickets file is damaged or edited into something unreadable, the program does
not delete it: it renames it to `tickets_<id>.json.<date-time>.bak`, tells you, and starts with no tickets.

## Project layout

| File | Purpose |
|---|---|
| `personalize.py` | Parameters generated from the employee ID that is entered (categories, SLA hours, prefix) |
| `models.py` | `Ticket` class, priorities, status flow, custom `InvalidTicketError` |
| `storage.py` | Saving and loading tickets as JSON |
| `helpdesk.py` | Business logic: raise, validate, update status, SLA, summary, filter |
| `main.py` | The interactive menu |
| `test_helpdesk.py` | Unit tests |
| `DESIGN_NOTE.md` | One-page design note |

## Our parameters (when employee ID 56040183 is entered)

- Categories: Hardware, VPN, Application Bug, Account Lockout, Access Request
- SLA hours: Critical 4, High 6, Medium 47, Low 108
- Ticket prefix: `SR`
