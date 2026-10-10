import os
import tempfile
import unittest
from datetime import datetime, timedelta

from helpdesk import Helpdesk
from models import InvalidTicketError, Ticket, make_ticket_id
from personalize import CATEGORIES, SLA_HOURS, TICKET_PREFIX, get_my_parameters
from storage import load_tickets, save_tickets


class HelpdeskTests(unittest.TestCase):
    def setUp(self):
        self.helpdesk = Helpdesk()
        self.category = CATEGORIES[0]

    def raise_one(self, priority="High"):
        return self.helpdesk.raise_ticket(self.category, priority, "Ann", "Printer jam")

    def test_parameters_are_deterministic(self):
        self.assertEqual(get_my_parameters("56040183"), get_my_parameters("56040183"))
        self.assertEqual(len(CATEGORIES), 5)

    def test_ticket_id_is_zero_padded_with_prefix(self):
        self.assertEqual(make_ticket_id("SR", 7), "SR-0007")
        self.assertEqual(self.raise_one().ticket_id, f"{TICKET_PREFIX}-0001")
        self.assertEqual(self.raise_one().ticket_id, f"{TICKET_PREFIX}-0002")

    def test_invalid_input_is_rejected(self):
        bad_inputs = [("Toaster", "High", "Ann", "x"), (self.category, "Urgent", "Ann", "x"),
                      (self.category, "High", "", "x"), (self.category, "High", "Ann", "   ")]
        for args in bad_inputs:
            with self.assertRaises(InvalidTicketError):
                self.helpdesk.raise_ticket(*args)
        self.assertEqual(self.helpdesk.tickets, [])

    def test_status_must_follow_the_flow(self):
        ticket = self.raise_one()
        with self.assertRaises(InvalidTicketError):
            self.helpdesk.update_status(ticket.ticket_id, "Closed")
        for status in ("In Progress", "Resolved", "Closed"):
            self.helpdesk.update_status(ticket.ticket_id, status)
        self.assertEqual(ticket.status, "Closed")
        with self.assertRaises(InvalidTicketError):
            self.helpdesk.update_status(ticket.ticket_id, "Open")

    def test_sla_breach_detection(self):
        ticket = self.raise_one("Critical")
        now = ticket.created_at
        self.assertFalse(self.helpdesk.is_breached(ticket, now))
        within = now + timedelta(hours=SLA_HOURS["Critical"])
        self.assertFalse(self.helpdesk.is_breached(ticket, within))
        late = within + timedelta(minutes=1)
        self.assertTrue(self.helpdesk.is_breached(ticket, late))
        self.helpdesk.update_status(ticket.ticket_id, "In Progress")
        self.helpdesk.update_status(ticket.ticket_id, "Resolved")
        self.assertFalse(self.helpdesk.is_breached(ticket, late))

    def test_summary_counts(self):
        first = self.raise_one("Critical")
        self.raise_one("Low")
        self.helpdesk.backdate_ticket(first.ticket_id, 100)
        summary = self.helpdesk.summary()
        self.assertEqual(summary["by_status"]["Open"], 2)
        self.assertEqual(summary["by_category"][self.category], 2)
        self.assertEqual(summary["breached"], [first.ticket_id])

    def test_filtering(self):
        self.raise_one("High")
        self.helpdesk.raise_ticket(CATEGORIES[1], "Low", "Bob", "VPN down")
        self.assertEqual(len(self.helpdesk.filter_tickets(priority="high")), 1)
        self.assertEqual(len(self.helpdesk.filter_tickets(category=CATEGORIES[1])), 1)
        self.assertEqual(len(self.helpdesk.filter_tickets(status="Closed")), 0)
        self.assertEqual(len(self.helpdesk.filter_tickets()), 2)

    def test_tickets_survive_save_and_load(self):
        self.raise_one()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "tickets.json")
            save_tickets(self.helpdesk.tickets, path)
            loaded = load_tickets(path)
        self.assertEqual([t.to_dict() for t in loaded],
                         [t.to_dict() for t in self.helpdesk.tickets])
        self.assertIsInstance(loaded[0], Ticket)
        self.assertIsInstance(loaded[0].created_at, datetime)

    def test_missing_or_corrupt_file_gives_empty_list(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "tickets.json")
            self.assertEqual(load_tickets(path), [])
            with open(path, "w") as file:
                file.write("not json")
            self.assertEqual(load_tickets(path), [])


if __name__ == "__main__":
    unittest.main()
