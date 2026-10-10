from helpdesk import Helpdesk, require_text
from models import InvalidTicketError
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


def ask(message, check):
    """Keep asking until check(answer) succeeds; show the error and re-prompt otherwise."""
    while True:
        try:
            return check(input(message))
        except InvalidTicketError as error:
            print(f"  Error: {error}")


def ask_number(message):
    """Ask for a positive number of hours, re-prompting on bad input."""
    while True:
        try:
            hours = float(input(message))
        except ValueError:
            print("  Error: please enter a number.")
        else:
            if hours > 0:
                return hours
            print("  Error: the number must be greater than zero.")


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
    ticket = ask("Ticket ID: ", helpdesk.find_ticket)
    print(f"Current: {ticket}")
    new_status = input("New status (Open/In Progress/Resolved/Closed): ")
    helpdesk.update_status(ticket.ticket_id, new_status)
    print(f"Updated: {ticket}")


def filter_menu(helpdesk):
    print("Leave a filter blank to skip it.")
    category = input("Category: ").strip() or None
    priority = input("Priority: ").strip() or None
    status = input("Status: ").strip() or None
    show_tickets(helpdesk, helpdesk.filter_tickets(category, priority, status))


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
    ticket = ask("Ticket ID: ", helpdesk.find_ticket)
    hours = ask_number("Move creation time back by how many hours? ")
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


def main():
    helpdesk = Helpdesk(load_tickets())
    print(f"Helpdesk started for employee {EMPLOYEE_ID} "
          f"({len(helpdesk.tickets)} saved tickets loaded).")
    print(f"SLA hours: {SLA_HOURS}")
    while True:
        print(MENU)
        try:
            choice = input("Choose an option: ").strip()
        except EOFError:
            choice = "0"
        if choice == "0":
            print("Goodbye!")
            break
        action = ACTIONS.get(choice)
        if action is None:
            print("Please choose a number from the menu.")
            continue
        try:
            action(helpdesk)
        except InvalidTicketError as error:
            print(f"Error: {error}")
        else:
            save_tickets(helpdesk.tickets)


if __name__ == "__main__":
    main()
