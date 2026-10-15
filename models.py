from datetime import datetime

PRIORITIES = ("Low", "Medium", "High", "Critical")
# Each status maps to the statuses a ticket may move to next. Keys keep lifecycle order.
STATUS_TRANSITIONS = {
    "Open": ("In Progress",),
    "In Progress": ("Resolved",),
    "Resolved": ("Closed", "Open"),   # a Resolved ticket can be closed or reopened
    "Closed": (),                     # final: nothing comes after Closed
}
TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"
TEXT_FIELDS = ("ticket_id", "category", "requester", "description")


class InvalidTicketError(Exception):
    """Raised when ticket input or a status change is not allowed."""


def make_ticket_id(prefix, number):
    """Build a zero-padded ticket ID, e.g. make_ticket_id('SR', 7) -> 'SR-0007'."""
    return f"{prefix}-{number:04d}"


class Ticket:
    def __init__(self, ticket_id, category, priority, requester, description,
                 created_at=None, status="Open"):
        self.ticket_id = ticket_id
        self.category = category
        self.priority = priority
        self.requester = requester
        self.description = description
        self.created_at = created_at or datetime.now().replace(microsecond=0)
        self.status = status

    def __str__(self):
        short_description = self.description[:40]
        if len(self.description) > 40:
            short_description += "..."
        return (f"{self.ticket_id} | {self.priority:<8} | {self.status:<11} | "
                f"{self.category} | {self.requester} | "
                f"{self.created_at:%Y-%m-%d %H:%M} | {short_description}")

    def to_dict(self):
        return {
            "ticket_id": self.ticket_id,
            "category": self.category,
            "priority": self.priority,
            "requester": self.requester,
            "description": self.description,
            "created_at": self.created_at.strftime(TIME_FORMAT),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data):
        if not all(isinstance(data[field], str) for field in TEXT_FIELDS):
            raise ValueError("saved ticket has a field that is not text")
        if data["priority"] not in PRIORITIES or data["status"] not in STATUS_TRANSITIONS:
            raise ValueError("unknown priority or status in saved ticket")
        return cls(
            ticket_id=data["ticket_id"],
            category=data["category"],
            priority=data["priority"],
            requester=data["requester"],
            description=data["description"],
            created_at=datetime.strptime(data["created_at"], TIME_FORMAT),
            status=data["status"],
        )
