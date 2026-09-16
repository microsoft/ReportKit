"""In-memory coverage of the audience renderers; no build or publication I/O."""

from __future__ import annotations

import copy
from hashlib import sha256
from html.parser import HTMLParser
import math
from pathlib import Path
import sys
import unittest
from urllib.parse import urlsplit

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from builtin_renderers import render_builtin_pages  # noqa: E402


TEMPLATES = ("action-risk", "portfolio-team", "operational-health", "compliance-readiness")


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.body = {}
        self.ids = []
        self.items = []
        self.links = []
        self.groups = {}
        self.tags = []
        self.text = []
        self.circles = []
        self.csp = ""
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag == "body":
            self.body = attrs
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if "data-item-id" in attrs:
            self.items.append(attrs["data-item-id"])
        if tag == "a":
            self.links.append(attrs["href"])
            if "data-group-id" in attrs:
                self.groups[attrs["data-group-id"]] = attrs["href"]
        if tag == "circle":
            self.circles.append((float(attrs["cx"]), float(attrs["cy"])))
        if tag == "meta" and attrs.get("http-equiv") == "Content-Security-Policy":
            self.csp = attrs["content"]
        self.assert_no_handler(attrs)

    def assert_no_handler(self, attrs):
        if any(key.lower().startswith("on") for key in attrs):
            raise AssertionError(f"Inline handler: {attrs}")

    def handle_data(self, data):
        self.text.append(data)


def model():
    items = [
        {"id": "overdue", "title": "Overdue critical", "status": "critical", "priority": "critical", "dueDate": "2026-09-14"},
        {"id": "today", "title": "Today's action", "status": "in-progress", "priority": "high", "dueDate": "2026-09-15", "groupIds": ["child"]},
        {"id": "end", "title": "Seventh-day review", "status": "pending-review", "dueDate": "2026-09-22"},
        {"id": "after", "title": "Later work", "status": "not-started", "dueDate": "2026-09-23"},
        {"id": "resolved", "title": "Completed work", "status": "complete", "dueDate": "2026-09-14"},
        {"id": "resolved-blocker", "title": "Healthy with explicit blocker", "status": "healthy", "blocker": "Source exception remains", "dueDate": "2026-09-14"},
        {"id": "unknown-overdue", "title": "Unknown assessment", "status": "unknown", "dueDate": "2026-09-14"},
        {"id": "blocked", "title": "Blocked, no date", "status": "blocked", "priority": "high"},
        {"id": "whitespace", "title": "Healthy without blocker", "status": "healthy", "blocker": "  ", "dueDate": "2026-09-14"},
    ]
    items[0].update({
        "summary": "Source summary <unsafe>",
        "accountableOwner": {"displayName": "Accountable Name", "alias": "accountable-alias", "team": "Accountable Team"},
        "actionOwner": {"displayName": "Action Name", "alias": "action-alias", "team": "Action Team"},
        "eta": "2026-09-21", "etaHealth": "at-risk", "ageDays": 12,
        "statusText": "Awaiting evidence", "nextAction": "Collect signed proof",
        "nextActionDate": "2026-09-16", "severity": "Sev2",
        "links": [{"label": "Source issue", "type": "source", "href": "https://example.invalid/issue?a=1&b=2"}],
        "evidence": [{"label": "Evidence artifact", "type": "evidence", "href": "https://example.invalid/proof"}],
    })
    return {
        "schemaVersion": "1.0",
        "report": {
            "id": "test-report", "title": "Canonical report", "subtitle": "Supplied snapshot",
            "classification": "Internal test", "generatedAt": "2026-09-14T23:30:00-02:00",
            "dataAsOf": "2026-09-15T00:30:00Z",
        },
        "items": items,
        "metrics": [
            {"id": f"metric-{index}", "label": f"Metric {index}", "value": index * 13, "unit": f"unit-{index}"}
            for index in range(6)
        ],
        "groups": [
            {"id": "root", "label": "Parent team", "itemIds": ["overdue"], "childGroupIds": ["child"], "page": "../../never-write.html", "accountableOwner": {"team": "Group Owners"}, "managementAction": "Confirm supplied milestone", "metricIds": ["metric-5"]},
            {"id": "child", "label": "Child team", "itemIds": ["overdue", "end"], "summary": "Child source summary", "status": "warning"},
            {"id": "empty", "label": "Empty team"},
        ],
        "trends": [
            {"id": "zero", "label": "Zero observations", "unit": "percent", "observations": [{"date": "2026-09-13", "value": 0}, {"date": "2026-09-14", "value": 0}]},
            {"id": "signed", "label": "Signed observations", "unit": "requests", "observations": [{"date": "2026-09-01", "value": -4}, {"date": "2026-09-03", "value": 0}, {"date": "2026-09-09", "value": 8}]},
        ],
        "highlights": [{"id": "change", "title": "Source-reported change", "type": "change", "summary": "A supplied event", "itemIds": ["overdue"], "groupIds": ["child"]}],
        "links": [{"label": "Report documentation", "type": "documentation", "href": "https://example.invalid/report"}],
        "provenance": {
            "adapter": {"id": "test-adapter", "version": "1.0"},
            "sources": [{"name": "Synthetic records", "type": "fixture", "retrievedAt": "2026-09-15T00:30:00Z", "recordCount": len(items)}],
            "recordCounts": {"raw": len(items), "normalized": len(items)},
        },
    }


class BuiltinRendererTests(unittest.TestCase):
    def render(self, template, value=None, config=None):
        return render_builtin_pages(template, value if value is not None else model(), config or {})

    def assert_valid_pages(self, pages, value):
        parsed = {name: Page(html) for name, html in pages.items()}
        self.assertIn("index.html", pages)
        for name, page in parsed.items():
            with self.subTest(page=name):
                self.assertRegex(name, r"^[a-z0-9-]+\.html$")
                self.assertEqual(len(page.ids), len(set(page.ids)))
                self.assertEqual(len(page.items), len(set(page.items)))
                self.assertEqual(str(len(value.get("items", []))), page.body["data-item-count"])
                self.assertEqual(str(len(page.items)), page.body["data-selected-item-count"])
                self.assertEqual(1, page.tags.count("h1"))
                self.assertEqual(1, page.tags.count("main"))
                self.assertNotIn("script", page.tags)
                self.assertTrue(page.csp.startswith("default-src 'none';"))
                for field in ("classification", "generatedAt", "dataAsOf"):
                    self.assertIn(value["report"][field], "".join(page.text))
                self.assertIn("Freshness:", "".join(page.text))
                for link in page.links:
                    target = urlsplit(link)
                    self.assertFalse(target.scheme, "Only generated report navigation is clickable.")
                    self.assertFalse(target.netloc, "External references must be text, not links.")
                    destination = target.path or name
                    self.assertIn(destination, parsed, link)
                    if target.fragment:
                        self.assertIn(target.fragment, parsed[destination].ids, link)

    def test_complete_pages_deterministic_safe_and_accessible(self):
        for template in TEMPLATES:
            with self.subTest(template=template):
                value = model()
                original = copy.deepcopy(value)
                first = self.render(template, value)
                self.assertEqual(first, self.render(template, value))
                self.assertEqual(original, value, "Rendering must not mutate canonical data.")
                self.assert_valid_pages(first, value)

    def test_action_filters_exact_membership_and_utc_boundaries(self):
        pages = self.render("action-risk")
        expected = {
            "index.html": {"overdue", "today", "end", "after", "resolved-blocker", "blocked"},
            "overdue.html": {"overdue", "resolved-blocker", "unknown-overdue"},
            "blocked.html": {"resolved-blocker", "blocked"},
            "due-next-seven-days.html": {"today", "end"},
            "all-records.html": {item["id"] for item in model()["items"]},
        }
        self.assertEqual(set(expected), set(pages))
        for name, ids in expected.items():
            with self.subTest(page=name):
                self.assertEqual(ids, set(Page(pages[name]).items))
                self.assertEqual(str(len(ids)), Page(pages[name]).body["data-selected-item-count"])
        self.assertIn("Snapshot UTC date: 2026-09-15", pages["index.html"])
        self.assertEqual("9", Page(pages["index.html"]).body["data-item-count"])
        for filename, ids in expected.items():
            self.assertIn(f'href="{filename}"><strong>{len(ids)}</strong>', pages["index.html"])

    def test_action_filters_honor_explicit_lifecycle(self):
        value = model()
        value["items"].extend([
            {
                "id": "closed-critical", "title": "Closed critical", "status": "critical",
                "lifecycle": "closed", "blocker": "Historical blocker", "dueDate": "2026-09-14",
            },
            {
                "id": "open-healthy", "title": "Open healthy", "status": "healthy",
                "lifecycle": "open", "dueDate": "2026-09-14",
            },
        ])
        pages = self.render("action-risk", value)
        attention = set(Page(pages["index.html"]).items)
        overdue = set(Page(pages["overdue.html"]).items)
        blocked = set(Page(pages["blocked.html"]).items)
        all_records = set(Page(pages["all-records.html"]).items)
        self.assertIn("open-healthy", attention)
        self.assertIn("open-healthy", overdue)
        self.assertNotIn("closed-critical", attention | overdue | blocked)
        self.assertTrue({"closed-critical", "open-healthy"}.issubset(all_records))

    def test_item_order_priority_blocker_due_then_id(self):
        value = model()
        value["items"] = [
            {"id": "z", "title": "Z", "status": "blocked", "priority": "high", "dueDate": "2026-09-13"},
            {"id": "b", "title": "B", "status": "warning", "priority": "high", "blocker": "Yes", "dueDate": "2026-09-15"},
            {"id": "a", "title": "A", "status": "warning", "priority": "high", "blocker": "Yes", "dueDate": "2026-09-15"},
            {"id": "critical", "title": "Critical", "status": "critical", "priority": "critical"},
        ]
        pages = self.render("action-risk", value)
        self.assertEqual(["critical", "a", "b", "z"], Page(pages["index.html"]).items)

    def test_portfolio_union_descendants_dedup_and_real_empty_pages(self):
        pages = self.render("portfolio-team")
        overview = Page(pages["index.html"])
        self.assertEqual({"root", "child", "empty"}, set(overview.groups))
        for group in model()["groups"]:
            filename = "group-" + sha256(group["id"].encode()).hexdigest() + ".html"
            self.assertEqual(filename, overview.groups[group["id"]])
        root = pages[overview.groups["root"]]
        child = pages[overview.groups["child"]]
        self.assertEqual({"overdue", "today", "end"}, set(Page(root).items))
        self.assertEqual({"overdue", "today", "end"}, set(Page(child).items))
        self.assertIn("Confirm supplied milestone", root)
        self.assertIn("Group Owners", root)
        self.assertIn("Metric 5", root)
        self.assertIn("65", root)
        self.assertIn("unit-5", root)
        self.assertIn("Child source summary", child)
        self.assertEqual([], Page(pages[overview.groups["empty"]]).items)
        self.assertIn("No records in this selection", pages[overview.groups["empty"]])
        self.assertEqual(
            {item["id"] for item in model()["items"]} - {"overdue", "today", "end"},
            set(overview.items),
        )
        self.assertNotIn("never-write.html", "".join(pages))

    def test_membership_cycle_guard_is_defensive(self):
        value = model()
        value["groups"][1]["childGroupIds"] = ["root"]
        pages = self.render("portfolio-team", value)
        self.assert_valid_pages(pages, value)
        self.assertEqual(5, len(pages))

    def test_all_metrics_values_units_targets_and_deltas_are_preserved(self):
        value = model()
        value["metrics"][0].update({
            "target": 25, "delta": {"value": -2, "unit": "points", "direction": "down", "assessment": "bad", "label": "Source comparison"},
        })
        for template in TEMPLATES:
            page = self.render(template, value)["index.html"]
            for metric in value["metrics"]:
                self.assertIn(f'data-metric-id="{metric["id"]}"', page)
                self.assertIn(metric["unit"], page)
                self.assertIn(f'>{metric["value"]}</p>', page)
            self.assertIn("25 unit-0", page)
            self.assertIn("-2 points", page)
            self.assertIn("Source comparison", page)
            self.assertIn("<dd>bad</dd>", page)
            self.assertIn("badge-unknown", page)

    def test_actual_chart_dates_signed_values_and_zero_baseline(self):
        pages = self.render("operational-health")
        page = Page(pages["index.html"])
        self.assertEqual(5, len(page.circles))
        self.assertEqual(page.circles[-2][1], page.circles[-1][1])
        self.assertEqual(136.0, page.circles[-1][1], "Zero values stay on the zero line, without a fake minimum bar.")
        signed = page.circles[:3]
        self.assertGreater(signed[0][1], signed[1][1])
        self.assertGreater(signed[1][1], signed[2][1])
        self.assertAlmostEqual((signed[1][0] - signed[0][0]) / (signed[2][0] - signed[0][0]), .25, places=3)
        text = "".join(page.text)
        for observation in model()["trends"][1]["observations"]:
            self.assertIn(observation["date"], text)
            self.assertIn(str(observation["value"]), text)
        self.assertIn("requests", text)
        self.assertIn("Solutions and recovery actions are unknown", text)

    def test_extreme_and_single_observation_charts_do_not_overflow(self):
        value = model()
        value["trends"] = [
            {"id": "extreme", "label": "Large observations", "unit": "units", "observations": [{"date": "2026-09-01", "value": -1e308}, {"date": "2026-09-02", "value": 1e308}]},
            {"id": "single", "label": "One observation", "unit": "units", "observations": [{"date": "2026-09-01", "value": -3}]},
        ]
        page = Page(self.render("operational-health", value)["index.html"])
        self.assertEqual(3, len(page.circles))
        self.assertTrue(all(math.isfinite(coordinate) for point in page.circles for coordinate in point))

    def test_no_status_owner_dates_or_actions_are_conflated(self):
        for template in TEMPLATES:
            pages = self.render(template)
            html = pages.get("all-records.html", pages["index.html"])
            text = "".join(Page(html).text)
            for expected in (
                "Accountable Name", "accountable-alias", "Accountable Team",
                "Action Name", "action-alias", "Action Team", "Awaiting evidence",
                "Collect signed proof", "2026-09-14", "2026-09-21", "2026-09-16",
                "Sev2", "12 days", "at-risk", "Source issue", "Evidence artifact",
            ):
                self.assertIn(expected, text, template)
            self.assertIn("Unknown / not supplied", text)
            self.assertIn("Unknown — no evidence supplied.", text)
            self.assertIn("badge-unknown", html, "Report status must remain unknown.")

    def test_empty_and_missing_collections_are_honest(self):
        for populated_empty in (False, True):
            value = model()
            for collection in ("items", "groups", "metrics", "trends", "highlights", "links"):
                if populated_empty:
                    value[collection] = []
                else:
                    value.pop(collection)
            for template in TEMPLATES:
                with self.subTest(template=template, empty=populated_empty):
                    pages = self.render(template, value)
                    self.assert_valid_pages(pages, value)
                    html = pages["index.html"]
                    self.assertIn("No metrics supplied.", html)
                    self.assertIn("No groups supplied.", html)
                    self.assertIn("No trend history supplied.", html)
                    self.assertIn("No highlights supplied.", html)
                    self.assertIn("No report links supplied.", html)
                    self.assertIn("badge-unknown", html)

    def test_html_escaping_and_unsafe_links_never_emitted(self):
        value = model()
        attack = '<script>alert("bad")</script>'
        value["report"]["title"] = attack
        value["items"][0]["title"] = attack
        value["items"][0]["accountableOwner"]["displayName"] = attack
        value["groups"][0]["summary"] = attack
        value["metrics"][0]["delta"] = {"value": attack}
        value["links"] = [
            {"type": "source", "label": attack, "href": href}
            for href in ("javascript:alert(1)", "data:text/html,bad", "file:///secret", "//evil.invalid", "https:\\\\evil.invalid", "\nhttps://example.invalid")
        ] + [
            {"type": "internal", "label": "Generated overview", "page": "index.html"},
            {"type": "internal", "label": "Unavailable hint", "page": "../../unsafe.html"},
        ]
        for template in TEMPLATES:
            pages = self.render(template, value)
            self.assert_valid_pages(pages, value)
            for html in pages.values():
                self.assertNotIn(attack, html)
                self.assertIn("&lt;script&gt;", html)
                self.assertNotRegex(html, r'href="(?:javascript|data|file):')
                self.assertNotIn('href="//', html)
                self.assertNotIn('href="../../', html)
                self.assertIn('href="index.html">Generated overview', html)
                self.assertIn("destination unavailable in this report", html)

    def test_source_urls_are_escaped_text_and_footer_identity_is_complete(self):
        value = model()
        for template in TEMPLATES:
            pages = self.render(template, value)
            self.assert_valid_pages(pages, value)
            html = pages.get("all-records.html", pages["index.html"])
            self.assertIn("https://example.invalid/issue?a=1&amp;b=2", html)
            self.assertNotIn('href="https:', html)
            self.assertNotIn('href="http:', html)
            for page in pages.values():
                footer = page.split("<footer>", 1)[1]
                for field in ("id", "generatedAt", "dataAsOf"):
                    self.assertIn(value["report"][field], footer)

    def test_requested_preview_notice_describes_generated_report(self):
        for template in TEMPLATES:
            pages = self.render(template, config={"output": {"includePrototypeNotice": True}})
            for html in pages.values():
                self.assertIn("Preview report", html)
                self.assertIn("Generated from canonical data for review.", html)
                self.assertNotIn("hand-authored", html)
            self.assertNotIn("Preview report", self.render(template)["index.html"])

    def test_compliance_preserves_evidence_and_does_not_invent_approval(self):
        value = model()
        value["items"][0]["category"] = "requirement"
        value["items"][0]["readinessGate"] = {"status": "in-progress", "decision": "hold"}
        html = self.render("compliance-readiness", value)["index.html"]
        self.assertEqual({item["id"] for item in value["items"]}, set(Page(html).items))
        self.assertEqual(1, html.count('class="requirement"'))
        self.assertIn("Evidence artifact", html)
        self.assertIn("exception approval state are not supplied", html)
        self.assertIn("No release approval", html)
        self.assertNotIn("Exceptions approved", html)
        self.assertEqual(len(model()["groups"]), html.count('<li><div><strong><a data-group-id='))

    def test_freshness_uses_inputs_and_config_only(self):
        value = model()
        value["report"]["dataAsOf"] = "2026-09-01T00:00:00Z"
        for template in TEMPLATES:
            for page in self.render(template, value).values():
                self.assertIn("Freshness: Stale", page)
        html = self.render("operational-health", config={"freshnessThresholdsMinutes": {"fresh": 0, "stale": 100}})["index.html"]
        self.assertIn("Freshness: Aging", html)
        self.assertIn("60 min old", html)

    def test_unknown_template_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown built-in renderer"):
            self.render("does-not-exist")


if __name__ == "__main__":
    unittest.main()
