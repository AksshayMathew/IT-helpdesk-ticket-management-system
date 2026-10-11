import math
import sys

from helpdesk import Helpdesk, match_option, require_text
from models import STATUS_FLOW, InvalidTicketError
from personalize import EMPLOYEE_ID, SLA_HOURS
from storage import load_tickets, save_tickets

MENU = """
===== IT Helpdesk =====
1. Raise a ticket
2. Update ticket status
3. List all tickets
4. Filter / search tickets
5. View summary
6. Backdate a ticket (demo SLA breach)
0. Exit
"""


def ask(message, check, allow_blank=False):
    """Keep asking until check(answer) succeeds; show the error and re-prompt otherwise.
    If allow_blank is True, pressing Enter on its own cancels and returns None."""
    while True:
        answer = input(message)
        if allow_blank and not answer.strip():
            return None
        try:
            return check(answer)
        except InvalidTicketError as error:
            print(f"  Error: {error}")


def ask_number(message, maximum=10000):
    """Ask for a number of hours between 0 and maximum, re-prompting on bad input.
    Pressing Enter on its own cancels and returns None."""
    while True:
        answer = input(message)
        if not answer.strip():
            return None
        try:
            hours = float(answer)
        except ValueError:
            print("  Error: please enter a number.")
        else:
            if math.isfinite(hours) and 0 < hours <= maximum:
                return hours
            print(f"  Error: the number must be greater than 0 and at most {maximum}.")


def show_tickets(helpdesk, tickets):
    if not tickets:
        print("No tickets found.")
    for ticket in tickets:
        flag = "  ** SLA BREACHED **" if helpdesk.is_breached(ticket) else ""
        print(f"{ticket}{flag}")


def raise_ticket_menu(helpdesk):
    print(f"Categories: {', '.join(helpdesk.categories)}")
    category = ask("Category: ", helpdesk.validate_category)
    priority = ask("Priority (Low/Medium/High/Critical): ", helpdesk.validate_priority)
    requester = ask("Requester name: ", lambda text: require_text(text, "Requester name"))
    description = ask("Description: ", lambda text: require_text(text, "Description"))
    ticket = helpdesk.raise_ticket(category, priority, requester, description)
    print(f"Created: {ticket}")


def update_status_menu(helpdesk):
    ticket = ask("Ticket ID (Enter to cancel): ", helpdesk.find_ticket, allow_blank=True)
    if ticket is None:
        return
    if helpdesk.next_status(ticket) is None:
        print(f"{ticket.ticket_id} is already Closed, so there is nothing left to update.")
        return
    print(f"Current: {ticket}")
    updated = ask("New status (Open/In Progress/Resolved/Closed, Enter to cancel): ",
                  lambda answer: helpdesk.update_status(ticket.ticket_id, answer),
                  allow_blank=True)
    if updated is not None:
        print(f"Updated: {ticket}")


def filter_menu(helpdesk):
    print("Leave a filter blank to skip it.")
    category = ask("Category: ", lambda text: text.strip() and helpdesk.validate_category(text))
    priority = ask("Priority: ", lambda text: text.strip() and helpdesk.validate_priority(text))
    status = ask("Status: ", lambda text: text.strip() and match_option(text, STATUS_FLOW, "status"))
    show_tickets(helpdesk, helpdesk.filter_tickets(category or None, priority or None, status or None))


def summary_menu(helpdesk):
    summary = helpdesk.summary()
    print("Tickets by status:")
    for status, count in summary["by_status"].items():
        print(f"  {status:<12} {count}")
    print("Tickets by category:")
    for category, count in summary["by_category"].items():
        print(f"  {category:<16} {count}")
    breached = summary["breached"]
    print(f"SLA-breached tickets ({len(breached)}): {', '.join(breached) or 'none'}")


def backdate_menu(helpdesk):
    ticket = ask("Ticket ID (Enter to cancel): ", helpdesk.find_ticket, allow_blank=True)
    if ticket is None:
        return
    hours = ask_number("Move creation time back by how many hours? (Enter to cancel) ")
    if hours is None:
        return
    helpdesk.backdate_ticket(ticket.ticket_id, hours)
    print(f"Updated: {ticket}")


ACTIONS = {
    "1": raise_ticket_menu,
    "2": update_status_menu,
    "3": lambda helpdesk: show_tickets(helpdesk, helpdesk.tickets),
    "4": filter_menu,
    "5": summary_menu,
    "6": backdate_menu,
}


def run_menu(helpdesk):
    while True:
        print(MENU)
        choice = input("Choose an option: ").strip()
        if choice == "0":
            return
        action = ACTIONS.get(choice)
        if action is None:
            print("Please choose a number from the menu.")
            continue
        try:
            action(helpdesk)
        except InvalidTicketError as error:
            print(f"Error: {error}")
        else:
            save_changes(helpdesk)


def save_changes(helpdesk):
    try:
        save_tickets(helpdesk.tickets)
    except OSError as error:
        print(f"Warning: could not save tickets ({error}).")


def main():
    try:
        helpdesk = Helpdesk(load_tickets())
    except OSError as error:
        print(f"Cannot read the saved tickets ({error}). Fix the problem and start again.")
        return
    print(f"Helpdesk started for employee {EMPLOYEE_ID} "
          f"({len(helpdesk.tickets)} saved tickets loaded).")
    print(f"SLA hours: {SLA_HOURS}")
    try:
        run_menu(helpdesk)
    except (EOFError, KeyboardInterrupt):
        print()
    print("Goodbye!")


if __name__ == "__main__":
    # Print "?" instead of crashing if the console or pipe cannot show a character (e.g. an emoji).
    sys.stdout.reconfigure(errors="replace")
    main()
