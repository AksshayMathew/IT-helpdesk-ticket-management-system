import json
import os
from datetime import datetime

from models import Ticket

DATA_FOLDER = os.path.dirname(os.path.abspath(__file__))


def data_path(employee_id):
    """Each employee has their own file next to the code, e.g. tickets_56040183.json."""
    return os.path.join(DATA_FOLDER, f"tickets_{employee_id}.json")


def save_tickets(tickets, path):
    """Write all tickets to a JSON file."""
    records = [ticket.to_dict() for ticket in tickets]
    with open(path, "w", encoding="utf-8") as file:
        json.dump(records, file, indent=2)


def load_tickets(path):
    """Read tickets from the JSON file; return an empty list if there is no usable data."""
    try:
        file = open(path, "r", encoding="utf-8-sig")
    except FileNotFoundError:
        return []
    try:
        records = json.load(file)
        if not isinstance(records, list):
            raise ValueError("the tickets file must contain a list")
        tickets = [Ticket.from_dict(record) for record in records]
    except (json.JSONDecodeError, KeyError, ValueError, TypeError):
        file.close()
        backup = f"{path}.{datetime.now():%Y%m%d-%H%M%S}.bak"
        os.replace(path, backup)
        print(f"Warning: {os.path.basename(path)} is unreadable. "
              f"Moved it to {os.path.basename(backup)} and starting with no tickets.")
        return []
    else:
        return tickets
    finally:
        file.close()
