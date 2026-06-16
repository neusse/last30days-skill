import unittest
from unittest.mock import patch

from lib import jobs


class JobsSourceTests(unittest.TestCase):
    def test_parse_greenhouse_response_preserves_core_fields(self):
        payload = {
            "jobs": [
                {
                    "id": 123,
                    "title": "Enterprise Security Engineer",
                    "updated_at": "2026-06-01T10:00:00-05:00",
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
                    "content": "<p>Build SSO and SOC 2 workflows.</p>",
                    "location": {"name": "Remote"},
                    "departments": [{"name": "Engineering"}],
                    "offices": [{"name": "US"}],
                }
            ]
        }
        parsed = jobs.parse_greenhouse_response(payload, board_token="acme")
        self.assertEqual(1, len(parsed))
        item = parsed[0]
        self.assertEqual("Enterprise Security Engineer", item["title"])
        self.assertEqual("2026-06-01", item["date"])
        self.assertEqual("Engineering", item["department"])
        self.assertIn("SSO", item["description"])
        self.assertEqual("greenhouse", item["provider"])

    @patch("lib.jobs.http.get")
    def test_greenhouse_404_degrades_to_empty(self, mock_get):
        mock_get.side_effect = jobs.http.HTTPError("missing", status_code=404)
        items, artifact = jobs.search_jobs(
            "MissingCo",
            ("2026-05-16", "2026-06-16"),
            {},
            web_backend="none",
        )
        self.assertEqual([], items)
        self.assertEqual(0, artifact["resultCount"])


if __name__ == "__main__":
    unittest.main()
