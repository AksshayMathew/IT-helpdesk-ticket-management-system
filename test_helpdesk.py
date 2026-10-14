import contextlib
import glob
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from unittest import mock

import main
from helpdesk import Helpdesk, require_employee_id
from models import InvalidTicketError, Ticket, make_ticket_id
from personalize import get_my_parameters
from storage import data_path, load_tickets, save_tickets

EMPLOYEE_ID = "56040183"
PARAMETERS = get_my_parameters(EMPLOYEE_ID)
CATEGORIES = PARAMETERS["categories"]
SLA_HOURS = PARAMETERS["sla_hours"]
TICKET_PREFIX = PARAMETERS["ticket_prefix"]


def load_quietly(path):
    """Call load_tickets but capture what it prints; return (tickets, printed text)."""
    printed = io.StringIO()
    with contextlib.redirect_stdout(printed):
        tickets = load_tickets(path)
    return tickets, printed.getvalue()


class HelpdeskTests(unittest.TestCase):
    def setUp(self):
        self.helpdesk = Helpdesk(EMPLOYEE_ID)
        self.category = CATEGORIES[0]

    def raise_one(self, priority="High"):
        return self.helpdesk.raise_ticket(self.category, priority, "Ann", "Printer jam")

    def test_parameters_are_deterministic(self):
        self.assertEqual(get_my_parameters("56040183"), get_my_parameters("56040183"))
        self.assertEqual(len(CATEGORIES), 5)

    def test_employee_id_is_checked(self):
        self.assertEqual(require_employee_id("  56040183 "), "56040183")
        self.assertEqual(require_employee_id("EMP1042"), "EMP1042")
        for bad in ("", "   ", "ab cd", "emp-1", "a/b", "..", "x" * 21, "éa", "²"):
            with self.assertRaises(InvalidTicketError):
                require_employee_id(bad)

    def test_each_employee_gets_their_own_parameters_and_file(self):
        mine, other = Helpdesk("56040183"), Helpdesk("EMP1042")
        self.assertEqual((mine.categories, mine.sla_hours, mine.prefix),
                         (CATEGORIES, SLA_HOURS, TICKET_PREFIX))
        self.assertNotEqual((mine.categories, mine.sla_hours, mine.prefix),
                            (other.categories, other.sla_hours, other.prefix))
        self.assertEqual(other.employee_id, "EMP1042")
        self.assertNotEqual(data_path("56040183"), data_path("EMP1042"))
        self.assertTrue(data_path("EMP1042").endswith("tickets_EMP1042.json"))

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
            self.assertEqual(load_quietly(path), ([], ""))
            with open(path, "w") as file:
                file.write("not json")
            tickets, printed = load_quietly(path)
        self.assertEqual(tickets, [])
        self.assertIn("unreadable", printed)

    def test_unusable_file_is_backed_up_not_lost(self):
        bad_contents = ['{"a": 1}', '[1, 2]', 'not json',
                        '[{"ticket_id": "SR-0001", "category": "VPN", "priority": "Bogus", '
                        '"requester": "a", "description": "d", '
                        '"created_at": "2026-01-01T00:00:00", "status": "Open"}]',
                        "null", "", "[{}]", '"just text"']
        for contents in bad_contents:
            with tempfile.TemporaryDirectory() as folder:
                path = os.path.join(folder, "tickets.json")
                with open(path, "w") as file:
                    file.write(contents)
                tickets, printed = load_quietly(path)
                self.assertEqual(tickets, [])
                self.assertFalse(os.path.exists(path))
                backups = glob.glob(path + ".*.bak")
                self.assertEqual(len(backups), 1)
                self.assertIn(os.path.basename(backups[0]), printed)
                with open(backups[0]) as backup:
                    self.assertEqual(backup.read(), contents)

    def test_ids_from_other_prefixes_are_ignored_when_numbering(self):
        self.helpdesk.tickets.append(
            Ticket("XX-abc", self.category, "High", "Ann", "odd id"))
        self.assertEqual(self.helpdesk.next_ticket_id(), f"{TICKET_PREFIX}-0001")

    def test_find_ticket_ignores_case_and_spaces(self):
        ticket = self.raise_one()
        self.assertIs(self.helpdesk.find_ticket(f"  {ticket.ticket_id.lower()} "), ticket)
        with self.assertRaises(InvalidTicketError):
            self.helpdesk.find_ticket("SR-9999")

    def test_ticket_numbering_continues_after_reload(self):
        self.raise_one()
        self.raise_one()
        reloaded = Helpdesk(EMPLOYEE_ID, [Ticket.from_dict(t.to_dict()) for t in self.helpdesk.tickets])
        self.assertEqual(reloaded.raise_ticket(self.category, "Low", "Bob", "x").ticket_id,
                         f"{TICKET_PREFIX}-0003")

    def test_backdated_ticket_is_breached_and_counted(self):
        ticket = self.raise_one("Low")
        self.helpdesk.backdate_ticket(ticket.ticket_id, SLA_HOURS["Low"] + 1)
        self.assertTrue(self.helpdesk.is_breached(ticket))
        self.assertIn(ticket, self.helpdesk.breached_tickets())

    def test_filter_rejects_unknown_values(self):
        for kwargs in ({"category": "Toaster"}, {"priority": "Urgent"}, {"status": "Done"}):
            with self.assertRaises(InvalidTicketError):
                self.helpdesk.filter_tickets(**kwargs)

    def test_combined_filters(self):
        self.raise_one("High")
        self.raise_one("Low")
        found = self.helpdesk.filter_tickets(category=self.category, priority="low", status="open")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].priority, "Low")
    def test_saved_ticket_with_non_text_field_is_rejected(self):
        good = self.raise_one().to_dict()
        for field, bad_value in (("description", 5), ("requester", None),
                                 ("category", ["VPN"]), ("ticket_id", 7)):
            with tempfile.TemporaryDirectory() as folder:
                path = os.path.join(folder, "tickets.json")
                with open(path, "w") as file:
                    json.dump([dict(good, **{field: bad_value})], file)
                self.assertEqual(load_quietly(path)[0], [])

    def test_file_saved_with_a_byte_order_mark_still_loads(self):
        good = self.raise_one().to_dict()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "tickets.json")
            with open(path, "w", encoding="utf-8-sig") as file:
                json.dump([good], file)
            tickets, printed = load_quietly(path)
        self.assertEqual([t.to_dict() for t in tickets], [good])
        self.assertEqual(printed, "")

    def test_oddly_numbered_ids_do_not_break_numbering(self):
        for odd_id in ("SR-\u00b2", "SR-", "SR-1a", "SR--5"):
            self.helpdesk.tickets.append(Ticket(odd_id, self.category, "High", "Ann", "odd"))
        self.assertEqual(self.helpdesk.next_ticket_id(), f"{TICKET_PREFIX}-0001")

    def test_numbering_goes_past_four_digits(self):
        self.helpdesk.tickets.append(
            Ticket(make_ticket_id(TICKET_PREFIX, 9999), self.category, "High", "Ann", "x"))
        self.assertEqual(self.helpdesk.next_ticket_id(), f"{TICKET_PREFIX}-10000")

    def test_next_status_for_every_state(self):
        ticket = self.raise_one()
        seen = []
        while self.helpdesk.next_status(ticket) is not None:
            seen.append(self.helpdesk.next_status(ticket))
            self.helpdesk.update_status(ticket.ticket_id, seen[-1])
        self.assertEqual(seen, ["In Progress", "Resolved", "Closed"])

    def test_backdating_too_far_is_rejected_not_a_crash(self):
        ticket = self.raise_one()
        with self.assertRaises(InvalidTicketError):
            self.helpdesk.backdate_ticket(ticket.ticket_id, 24 * 365 * 3000)
        self.assertGreater(ticket.created_at.year, 2000)


def run_menu_with(inputs, tickets=None):
    """Run the CLI menu with scripted keyboard input; return the printed text."""
    helpdesk = Helpdesk(EMPLOYEE_ID, tickets if tickets is not None else [])
    output = io.StringIO()
    with mock.patch("builtins.input", side_effect=inputs), \
            mock.patch("main.save_tickets"), contextlib.redirect_stdout(output):
        main.run_menu(helpdesk)
    return helpdesk, output.getvalue()


class MenuTests(unittest.TestCase):
    def setUp(self):
        self.category = CATEGORIES[0]

    def test_raise_ticket_reprompts_until_input_is_valid(self):
        helpdesk, printed = run_menu_with(
            ["1", "toaster", self.category.lower(), "urgent", "high", "", "Ann", "  ",
             "Printer jam", "0"])
        self.assertEqual(len(helpdesk.tickets), 1)
        ticket = helpdesk.tickets[0]
        self.assertEqual((ticket.category, ticket.priority, ticket.requester, ticket.description),
                         (self.category, "High", "Ann", "Printer jam"))
        for message in ("Invalid category 'toaster'", "Invalid priority 'urgent'",
                        "Requester name cannot be empty", "Description cannot be empty"):
            self.assertIn(message, printed)

    def test_update_and_backdate_can_be_cancelled_with_enter(self):
        helpdesk, printed = run_menu_with(["2", "", "6", "", "2", "SR-9999", "", "0"])
        self.assertIn("No ticket found with ID 'SR-9999'", printed)
        self.assertEqual(helpdesk.tickets, [])

    def test_closed_ticket_is_not_a_dead_end(self):
        ticket = Ticket("SR-0001", self.category, "Low", "Ann", "done", status="Closed")
        _, printed = run_menu_with(["2", "SR-0001", "0"], [ticket])
        self.assertIn("already Closed", printed)
        self.assertNotIn("New status", printed)

    def test_status_prompt_reprompts_then_can_be_cancelled(self):
        ticket = Ticket("SR-0001", self.category, "Low", "Ann", "x")
        _, printed = run_menu_with(["2", "SR-0001", "Closed", "bogus", "", "0"], [ticket])
        self.assertEqual(ticket.status, "Open")
        self.assertIn("Cannot move SR-0001", printed)
        self.assertIn("Invalid status 'bogus'", printed)

    def test_backdate_rejects_bad_numbers(self):
        ticket = Ticket("SR-0001", self.category, "Low", "Ann", "x")
        original = ticket.created_at
        bad_numbers = ["abc", "0", "-5", "inf", "nan", "1e400", "10001"]
        _, printed = run_menu_with(["6", "SR-0001"] + bad_numbers + ["2", "0"], [ticket])
        self.assertEqual(printed.count("Error:"), len(bad_numbers))
        self.assertEqual(ticket.created_at, original - timedelta(hours=2))

    def test_filter_menu_reprompts_on_bad_value_and_blank_skips(self):
        tickets = [Ticket("SR-0001", self.category, "Low", "Ann", "x"),
                   Ticket("SR-0002", CATEGORIES[1], "High", "Bob", "y")]
        _, printed = run_menu_with(["4", "toaster", "", "", "", "0"], tickets)
        self.assertIn("Invalid category 'toaster'", printed)
        self.assertIn("SR-0001", printed)
        self.assertIn("SR-0002", printed)

    def test_unknown_menu_choice_is_handled(self):
        _, printed = run_menu_with(["9", "abc", "", "0"])
        self.assertEqual(printed.count("Please choose a number from the menu."), 3)

    def test_ending_input_mid_prompt_exits_cleanly(self):
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=[EMPLOYEE_ID, "1", "vpn", EOFError]), \
                mock.patch("main.load_tickets", return_value=[]), \
                mock.patch("main.save_tickets"), contextlib.redirect_stdout(output):
            main.main()
        self.assertIn("Goodbye!", output.getvalue())

    def test_ending_input_at_the_employee_id_prompt_exits_cleanly(self):
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=EOFError), contextlib.redirect_stdout(output):
            main.main()
        self.assertTrue(output.getvalue().startswith("Welcome to HCL Tech IT Support System"))
        self.assertIn("Goodbye!", output.getvalue())

    def test_unreadable_tickets_file_gives_a_message_not_a_crash(self):
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=[EMPLOYEE_ID]), \
                mock.patch("main.load_tickets", side_effect=PermissionError("locked")), \
                contextlib.redirect_stdout(output):
            main.main()
        self.assertIn("Cannot read the saved tickets", output.getvalue())

    def test_save_failure_only_warns(self):
        output = io.StringIO()
        with mock.patch("main.save_tickets", side_effect=OSError("disk full")), \
                contextlib.redirect_stdout(output):
            main.save_changes(Helpdesk(EMPLOYEE_ID))
        self.assertIn("could not save", output.getvalue())

    def test_welcome_then_asks_for_employee_id_until_valid(self):
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=["", "bad id!", "x" * 21, "  " + EMPLOYEE_ID + " ", "0"]), \
                mock.patch("main.load_tickets", return_value=[]) as loader, \
                mock.patch("main.save_tickets"), contextlib.redirect_stdout(output):
            main.main()
        printed = output.getvalue()
        self.assertTrue(printed.startswith("Welcome to HCL Tech IT Support System"))
        self.assertIn("Employee ID cannot be empty", printed)
        self.assertEqual(printed.count("must be 1 to 20 letters or digits"), 2)
        self.assertIn(f"Hello, employee {EMPLOYEE_ID}", printed)
        loader.assert_called_once_with(data_path(EMPLOYEE_ID))

    def test_another_employee_gets_their_own_parameters_and_file(self):
        other = "EMP1042"
        output = io.StringIO()
        with mock.patch("builtins.input", side_effect=[other, "0"]), \
                mock.patch("main.load_tickets", return_value=[]) as loader, \
                mock.patch("main.save_tickets"), contextlib.redirect_stdout(output):
            main.main()
        loader.assert_called_once_with(data_path(other))
        self.assertIn(str(get_my_parameters(other)["sla_hours"]), output.getvalue())

    def test_changes_are_saved_to_the_employees_own_file(self):
        with mock.patch("main.save_tickets") as saver:
            main.save_changes(Helpdesk("EMP1042", []))
        saver.assert_called_once_with([], data_path("EMP1042"))


if __name__ == "__main__":
    unittest.main()
