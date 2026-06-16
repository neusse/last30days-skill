import unittest

from lib import render, schema


class RenderHiringSignalsTests(unittest.TestCase):
    def test_render_hiring_signals_block_with_citations(self):
        report = schema.Report(
            topic="Listen Labs",
            range_from="2026-05-16",
            range_to="2026-06-16",
            generated_at="2026-06-16T00:00:00Z",
            provider_runtime=schema.ProviderRuntime("mock", "mock", "mock"),
            query_plan=schema.QueryPlan(
                intent="product",
                freshness_mode="balanced_recent",
                cluster_mode="none",
                raw_topic="Listen Labs",
                subqueries=[],
                source_weights={},
            ),
            clusters=[],
            ranked_candidates=[],
            items_by_source={},
            errors_by_source={},
            artifacts={
                "hiring_signals": {
                    "mode": "standard",
                    "company_size_tier": "startup",
                    "include": True,
                    "signals": [
                        {
                            "theme": "enterprise readiness",
                            "interpretation": "appears to be increasing focus on enterprise readiness",
                            "confidence": "medium",
                            "evidence_count": 2,
                            "evidence": [
                                {
                                    "title": "Enterprise Security Engineer",
                                    "url": "https://example.com/jobs/1",
                                    "department": "Engineering",
                                    "published_at": "2026-06-01",
                                }
                            ],
                        }
                    ],
                }
            },
        )
        block = "\n".join(render._render_hiring_signals(report))
        self.assertIn("Hiring Signals", block)
        self.assertIn("[Enterprise Security Engineer](https://example.com/jobs/1)", block)
        self.assertIn("not exact roadmap predictions", block)
        html_md = render.render_for_html(report)
        self.assertIn("Hiring Signals", html_md)
        self.assertIn("[Enterprise Security Engineer](https://example.com/jobs/1)", html_md)

    def test_standard_mode_omits_weak_signal(self):
        report = schema.Report(
            topic="Apple",
            range_from="2026-05-16",
            range_to="2026-06-16",
            generated_at="2026-06-16T00:00:00Z",
            provider_runtime=schema.ProviderRuntime("mock", "mock", "mock"),
            query_plan=schema.QueryPlan(
                intent="product",
                freshness_mode="balanced_recent",
                cluster_mode="none",
                raw_topic="Apple",
                subqueries=[],
                source_weights={},
            ),
            clusters=[],
            ranked_candidates=[],
            items_by_source={},
            errors_by_source={},
            artifacts={
                "hiring_signals": {
                    "mode": "standard",
                    "company_size_tier": "mega-cap",
                    "include": False,
                    "signals": [],
                    "omitted_reason": "jobs evidence is too diffuse",
                }
            },
        )
        self.assertEqual([], render._render_hiring_signals(report))


if __name__ == "__main__":
    unittest.main()
