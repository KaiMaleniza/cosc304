import unittest
from unittest.mock import patch

from app import app
from routes.admin import parse_report_dates


class FakeCursor:
    def __init__(self):
        self.calls = 0

    def execute(self, sql, parameters=None):
        self.calls += 1

    def fetchall(self):
        return [(2026, 11, 20, 125.50, 3), (2026, 11, 21, 80.25, 2)]

    def fetchone(self):
        return (205.75, 5)


class FakeConnection:
    def __init__(self):
        self.cursor_instance = FakeCursor()

    def cursor(self):
        return self.cursor_instance

    def close(self):
        pass


class AdminReportTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)

    def test_parse_report_dates_accepts_valid_range(self):
        start, end, error = parse_report_dates("2026-11-01", "2026-11-21")
        self.assertEqual(start.isoformat(), "2026-11-01")
        self.assertEqual(end.isoformat(), "2026-11-21")
        self.assertIsNone(error)

    def test_parse_report_dates_rejects_inverted_range(self):
        start, end, error = parse_report_dates("2026-11-21", "2026-11-01")
        self.assertIsNone(start)
        self.assertIsNone(end)
        self.assertIn("on or before", error)

    @patch("routes.admin.require_login", return_value=None)
    @patch("routes.admin.get_connection")
    def test_admin_report_returns_summary_and_filtered_rows(self, get_connection, _require_login):
        get_connection.return_value = FakeConnection()
        with app.test_client() as client:
            with client.session_transaction() as session:
                session["authenticatedUser"] = "tester"
            response = client.get("/admin?start=2026-11-01&end=2026-11-21")

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Sales summary", html)
        self.assertIn("$205.75", html)
        self.assertIn("2026-11-20", html)

    @patch("routes.admin.require_login", return_value=None)
    def test_admin_report_rejects_inverted_range(self, _require_login):
        with app.test_client() as client:
            response = client.get("/admin?start=2026-11-21&end=2026-11-01")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Start date must be on or before", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
