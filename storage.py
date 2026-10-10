import json
import os

from models import Ticket

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tickets.json")


def save_tickets(tickets, path=DATA_FILE):
    """Write all tickets to a JSON file."""
    records = [ticket.to_dict() for ticket in tickets]
    with open(path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)


def load_tickets(path=DATA_FILE):
    """Read tickets from the JSON file; return an empty list if there is no usable data."""
    try:
        file = open(path, "r", encoding="utf-8")
    except FileNotFoundError:
        return []
    try:
        records = json.load(file)
        tickets = [Ticket.from_dict(record) for record in records]
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        file.close()
        backup = path + ".bak"
        os.replace(path, backup)
        print(f"Warning: {os.path.basename(path)} is unreadable. "
              f"Moved it to {os.path.basename(backup)} and starting with no tickets.")
        return []
    else:
        return tickets
    finally:
        file.close()
