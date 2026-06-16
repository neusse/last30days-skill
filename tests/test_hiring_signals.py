import unittest

from lib import hiring_signals, schema


def job(title: str, body: str, department: str = "Engineering") -> schema.SourceItem:
    return schema.SourceItem(
        item_id=title,
        source="jobs",
        title=title,
        body=body,
        url=f"https://example.com/jobs/{title.replace(' ', '-').lower()}",
        container=department,
        published_at="2026-06-01",
        date_confidence="high",
        metadata={"department": department},
    )


class HiringSignalsTests(unittest.TestCase):
    def test_startup_cluster_surfaces_in_standard_mode(self):
        items = [
            job("Founding Enterprise Solutions Engineer", "SSO SOC 2 procurement enterprise", "Sales"),
            job("Security Platform Engineer", "enterprise security audit admin", "Engineering"),
        ]
        summary = hiring_signals.analyze(items, explicit=False, topic="Listen Labs")
        self.assertTrue(summary["include"])
        self.assertEqual("startup", summary["company_size_tier"])
        self.assertEqual("enterprise readiness", summary["signals"][0]["theme"])

    def test_mega_cap_scattered_roles_do_not_surface_standard_mode(self):
        items = [
            job("Retail Associate", "store operations", "Retail"),
            job("iOS Engineer", "mobile app", "Engineering"),
            job("Finance Analyst", "planning", "Finance"),
        ]
        summary = hiring_signals.analyze(items, explicit=False, topic="Apple")
        self.assertFalse(summary["include"])
        self.assertEqual("mega-cap", summary["company_size_tier"])
        self.assertIn("too diffuse", summary["omitted_reason"])

    def test_explicit_mode_keeps_low_confidence_signal(self):
        items = [job("Customer Success Manager", "support enterprise customers", "Success")]
        summary = hiring_signals.analyze(items, explicit=True, topic="Acme")
        self.assertTrue(summary["include"])
        self.assertEqual("low", summary["signals"][0]["confidence"])


if __name__ == "__main__":
    unittest.main()
