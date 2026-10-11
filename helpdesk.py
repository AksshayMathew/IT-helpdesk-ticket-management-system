from datetime import datetime, timedelta

from models import (PRIORITIES, STATUS_FLOW, InvalidTicketError, Ticket,
                    make_ticket_id)
from personalize import CATEGORIES, SLA_HOURS, TICKET_PREFIX

CLOSED_STATES = {"Resolved", "Closed"}


def match_option(value, options, label):
    """Return the option that equals value (ignoring case/spaces) or raise an error."""
    cleaned = value.strip().lower()
    for option in options:
        if option.lower() == cleaned:
            return option
    raise InvalidTicketError(f"Invalid {label} '{value.strip()}'. Choose one of: {', '.join(options)}")


def require_text(value, label):
    """Return the stripped text or raise an error if it is empty."""
    cleaned = value.strip()
    if not cleaned:
        raise InvalidTicketError(f"{label} cannot be empty.")
    return cleaned


class Helpdesk:
    def __init__(self, tickets=None, categories=CATEGORIES, sla_hours=SLA_HOURS,
                 prefix=TICKET_PREFIX):
        self.tickets = tickets if tickets is not None else []
        self.categories = categories
        self.sla_hours = sla_hours
        self.prefix = prefix

    def validate_category(self, value):
        return match_option(value, self.categories, "category")

    def validate_priority(self, value):
        return match_option(value, PRIORITIES, "priority")

    def next_ticket_id(self):
        """Next free ID: highest number in use + 1 (so IDs never repeat after a restart)."""
        start = len(self.prefix) + 1
        used_numbers = [int(ticket.ticket_id[start:]) for ticket in self.tickets
                        if ticket.ticket_id.startswith(self.prefix + "-")
                        and ticket.ticket_id[start:].isdecimal()]
        return make_ticket_id(self.prefix, max(used_numbers, default=0) + 1)

    def raise_ticket(self, category, priority, requester, description):
        ticket = Ticket(
            ticket_id=self.next_ticket_id(),
            category=self.validate_category(category),
            priority=self.validate_priority(priority),
            requester=require_text(requester, "Requester name"),
            description=require_text(description, "Description"),
        )
        self.tickets.append(ticket)
        return ticket

    def find_ticket(self, ticket_id):
        for ticket in self.tickets:
            if ticket.ticket_id.lower() == ticket_id.strip().lower():
                return ticket
        raise InvalidTicketError(f"No ticket found with ID '{ticket_id.strip()}'.")

    def update_status(self, ticket_id, new_status):
        """Move a ticket one step forward: Open -> In Progress -> Resolved -> Closed."""
        ticket = self.find_ticket(ticket_id)
        new_status = match_option(new_status, STATUS_FLOW, "status")
        allowed = self.next_status(ticket)
        if allowed is None:
            raise InvalidTicketError(f"{ticket.ticket_id} is already Closed.")
        if new_status != allowed:
            raise InvalidTicketError(
                f"Cannot move {ticket.ticket_id} from '{ticket.status}' to '{new_status}'. "
                f"Next allowed status: {allowed}.")
        ticket.status = new_status
        return ticket

    def next_status(self, ticket):
        """The only status the ticket may move to next, or None if it is already Closed."""
        next_index = STATUS_FLOW.index(ticket.status) + 1
        return STATUS_FLOW[next_index] if next_index < len(STATUS_FLOW) else None

    def is_breached(self, ticket, now=None):
        """An unresolved ticket is breached once now passes created time + its SLA hours."""
        if ticket.status in CLOSED_STATES:
            return False
        now = now or datetime.now()
        deadline = ticket.created_at + timedelta(hours=self.sla_hours[ticket.priority])
        return now > deadline

    def breached_tickets(self, now=None):
        return [ticket for ticket in self.tickets if self.is_breached(ticket, now)]

    def backdate_ticket(self, ticket_id, hours):
        """Demo helper: pretend a ticket was created `hours` ago so an SLA breach can be shown."""
        ticket = self.find_ticket(ticket_id)
        try:
            ticket.created_at -= timedelta(hours=hours)
        except OverflowError:
            raise InvalidTicketError("That would move the creation time too far into the past.")
        return ticket

    def summary(self, now=None):
        """Ticket counts by status and by category, plus the SLA-breached tickets."""
        return {
            "by_status": {status: len([t for t in self.tickets if t.status == status])
                          for status in STATUS_FLOW},
            "by_category": {category: len([t for t in self.tickets if t.category == category])
                            for category in self.categories},
            "breached": [t.ticket_id for t in self.breached_tickets(now)],
        }

    def filter_tickets(self, category=None, priority=None, status=None):
        """Return tickets matching every filter that was given (None means 'any')."""
        if category is not None:
            category = self.validate_category(category)
        if priority is not None:
            priority = self.validate_priority(priority)
        if status is not None:
            status = match_option(status, STATUS_FLOW, "status")
        return [t for t in self.tickets
                if (category is None or t.category == category)
                and (priority is None or t.priority == priority)
                and (status is None or t.status == status)]
