#!/usr/bin/env python3
"""Create the deterministic, non-sensitive 401-record ReportKit sample."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path


GROUPS = [
    ("platform-readiness", "Platform Readiness", 62, 12, 4),
    ("release-engineering", "Release Engineering", 56, 10, 3),
    ("workload-identity", "Workload Identity", 52, 8, 2),
    ("cloud-readiness", "Cloud Readiness", 48, 6, 1),
    ("service-integration", "Service Integration", 55, 5, 1),
    ("observability", "Observability", 45, 4, 1),
    ("compliance-operations", "Compliance Operations", 39, 2, 0),
    ("developer-experience", "Developer Experience", 44, 2, 0),
]


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    destination = root / "examples" / "operational-snapshot"
    destination.mkdir(parents=True, exist_ok=True)

    items = []
    groups = []
    cursor = 1
    base_due = date(2026, 9, 15)
    for group_order, (group_id, label, total, attention, critical) in enumerate(GROUPS, 1):
        item_ids = []
        for local_index in range(total):
            item_id = f"REC-{cursor:03d}"
            item_ids.append(item_id)
            if local_index < critical:
                status = "critical"
                priority = "critical"
            elif local_index < attention:
                status = "warning"
                priority = "high"
            else:
                status = "healthy"
                priority = "low"
            due = base_due + timedelta(days=(local_index % 15) - 3)
            title = (
                "Validate escaped source text <unsafe-test>"
                if cursor == 1
                else f"{label} operational record {local_index + 1}"
            )
            items.append({
                "id": item_id,
                "title": title,
                "summary": (
                    f"Synthetic, non-sensitive {status} record used to demonstrate "
                    "the ReportKit canonical model."
                ),
                "status": status,
                "priority": priority,
                "accountableOwner": {"team": label},
                "actionOwner": {"displayName": f"Sample Owner {(cursor % 12) + 1}"},
                "dueDate": due.isoformat(),
                "eta": (due + timedelta(days=1 if status != "healthy" else -1)).isoformat(),
                "etaHealth": "at-risk" if status != "healthy" else "on-track",
                "statusText": "Attention required." if status != "healthy" else "Operating as expected.",
                "nextAction": (
                    "Confirm remediation evidence and close the decision."
                    if status != "healthy"
                    else "Continue planned monitoring."
                ),
                "nextActionDate": (base_due + timedelta(days=(local_index % 7) + 1)).isoformat(),
                "blocker": "Shared validation capacity" if status == "critical" else None,
                "ageDays": (local_index % 30) + 1,
                "groupIds": [group_id],
                "links": [{
                    "label": "Synthetic source record",
                    "type": "source",
                    "href": f"https://example.com/reportkit/records/{item_id}"
                }]
            })
            cursor += 1
        groups.append({
            "id": group_id,
            "label": label,
            "type": "program",
            "status": "critical" if critical else ("warning" if attention else "healthy"),
            "summary": f"{attention} of {total} synthetic records require attention.",
            "accountableOwner": {"team": label},
            "itemIds": item_ids,
            "managementAction": (
                "Review the highest-priority records and confirm the recovery path."
                if attention else "Continue planned monitoring."
            ),
            "order": group_order,
            "page": f"{group_id}.html"
        })

    model = {
        "schemaVersion": "1.0",
        "report": {
            "id": "operational-portfolio-2026-09-15",
            "title": "Engineering Portfolio Health",
            "subtitle": "Synthetic 401-record operational snapshot",
            "generatedAt": "2026-09-15T18:00:00Z",
            "dataAsOf": "2026-09-15T17:55:00Z",
            "period": {
                "label": "Week ending 15 September 2026",
                "startDate": "2026-09-09",
                "endDate": "2026-09-15"
            },
            "status": "warning",
            "statusLabel": "Requires attention",
            "statusSummary": (
                "87.8% of records are healthy. Twelve critical records across six "
                "programs require leadership review."
            ),
            "classification": "Public sample"
        },
        "metrics": [
            {
                "id": "portfolio-coverage", "label": "Portfolio coverage", "value": 401,
                "unit": "raw records", "status": "healthy", "order": 1,
                "description": "Complete synthetic coverage across all eight programs."
            },
            {
                "id": "healthy", "label": "Healthy", "value": 352,
                "unit": "raw records · 87.8%", "status": "healthy", "order": 2,
                "description": "Records currently operating within the sample health criteria."
            },
            {
                "id": "needs-attention", "label": "Needs attention", "value": 37,
                "unit": "raw records · 9.2%", "status": "warning", "order": 3,
                "description": "Warning records requiring follow-through."
            },
            {
                "id": "critical", "label": "Critical", "value": 12,
                "unit": "raw records · 3.0%", "status": "critical", "order": 4,
                "description": "Critical records requiring leadership review."
            }
        ],
        "groups": groups,
        "items": items,
        "trends": [{
            "id": "healthy-share",
            "label": "Healthy share by weekly snapshot",
            "unit": "percent",
            "status": "healthy",
            "order": 1,
            "observations": [
                {"date": "2026-07-28", "value": 78.0},
                {"date": "2026-08-04", "value": 79.5},
                {"date": "2026-08-11", "value": 81.0},
                {"date": "2026-08-18", "value": 82.7},
                {"date": "2026-08-25", "value": 84.1},
                {"date": "2026-09-01", "value": 85.8},
                {"date": "2026-09-08", "value": 86.9},
                {"date": "2026-09-15", "value": 87.8}
            ]
        }],
        "highlights": [
            {
                "id": "coverage-complete", "title": "Coverage reached 100%",
                "summary": "All eight synthetic programs supplied a complete snapshot.",
                "type": "win", "status": "healthy", "order": 1
            },
            {
                "id": "healthy-improved", "title": "Healthy share improved",
                "summary": "The synthetic healthy share rose to 87.8%.",
                "type": "change", "status": "healthy", "order": 2
            },
            {
                "id": "critical-review", "title": "Twelve records require review",
                "summary": "Critical records are concentrated in six programs.",
                "type": "decision", "status": "critical", "order": 3
            }
        ],
        "links": [],
        "provenance": {
            "adapter": {"id": "synthetic-operational-snapshot", "version": "1.0"},
            "sources": [{
                "type": "generated-sample",
                "name": "ReportKit public synthetic sample",
                "retrievedAt": "2026-09-15T17:55:00Z",
                "recordCount": 401
            }],
            "recordCounts": {
                "raw": 401,
                "healthy": 352,
                "warning": 37,
                "critical": 12,
                "groups": 8
            }
        }
    }
    config = {
        "version": "1.0",
        "template": {"id": "executive-health", "version": "1.0"},
        "theme": {"name": "reportkit-default", "primaryColor": "#2875e2"},
        "freshnessThresholdsMinutes": {"fresh": 60, "stale": 1440},
        "output": {"selfContained": True, "includePrototypeNotice": False}
    }
    write_json(destination / "canonical-report.json", model)
    write_json(destination / "executive-health.config.json", config)
    print(f"Wrote {len(items)} canonical records to {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

