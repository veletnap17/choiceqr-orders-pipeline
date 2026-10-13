import unittest
from unittest.mock import Mock, patch

import main


class TestChoiceQRFetch(unittest.TestCase):
    def response(self, status, orders=None, headers=None):
        response = Mock(status_code=status, headers=headers or {})
        response.json.return_value = {"orders": orders if orders is not None else []}
        if status >= 400:
            response.raise_for_status.side_effect = main.requests.HTTPError(f"HTTP {status}")
        return response

    @patch("main.time.sleep")
    def test_pagination_and_restaurant_metadata(self, sleep):
        session = Mock()
        session.get.side_effect = [self.response(200, [{"_id": "1"}]), self.response(200, [])]
        rows = main.fetch_orders_for_restaurant("Vinohrady", "token", "2026-10-01", "2026-10-02", session)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["restaurant"], "Vinohrady")
        self.assertIn("loaded_at", rows[0])
        self.assertEqual(session.get.call_count, 2)

    @patch("main.time.sleep")
    def test_429_then_success(self, sleep):
        session = Mock()
        session.get.side_effect = [self.response(429, headers={"Retry-After": "3"}), self.response(200, [])]
        self.assertEqual(main.fetch_orders_for_restaurant("A", "token", "a", "b", session), [])
        sleep.assert_called_once_with(3.0)

    @patch("main.time.sleep")
    def test_429_exhausted(self, sleep):
        session = Mock()
        session.get.return_value = self.response(429)
        with self.assertRaisesRegex(RuntimeError, "rate limit persisted"):
            main.fetch_orders_for_restaurant("A", "token", "a", "b", session)
        self.assertEqual(session.get.call_count, main.MAX_RETRIES + 1)

    def test_http_400_is_not_end_of_pages(self):
        session = Mock()
        session.get.return_value = self.response(400)
        with self.assertRaises(main.requests.HTTPError):
            main.fetch_orders_for_restaurant("A", "token", "a", "b", session)

    def test_missing_token(self):
        self.assertEqual(main.fetch_orders_for_restaurant("A", None, "a", "b"), [])

    def test_invalid_payload(self):
        session = Mock()
        session.get.return_value = self.response(200)
        session.get.return_value.json.return_value = {"orders": {}}
        with self.assertRaisesRegex(ValueError, "orders must be a list"):
            main.fetch_orders_for_restaurant("A", "token", "a", "b", session)


if __name__ == "__main__":
    unittest.main()
