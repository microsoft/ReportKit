#!/usr/bin/env python3
"""Create static companion pages referenced by the approved design prototypes."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path


PAGE_TITLES = {
    "portfolio-team-platform-readiness.html": "Platform Readiness",
    "portfolio-team-release-engineering.html": "Release Engineering",
    "portfolio-team-workload-identity.html": "Workload Identity",
    "portfolio-team-cloud-readiness.html": "Cloud Readiness",
    "portfolio-team-service-integration.html": "Service Integration",
    "portfolio-team-observability.html": "Observability",
    "portfolio-team-compliance-operations.html": "Compliance Operations",
    "portfolio-team-developer-experience.html": "Developer Experience",
    "portfolio-team-states.html": "Portfolio state reference",
    "operational-health-states.html": "Operational state reference",
    "compliance-readiness-states.html": "Compliance state reference",
}


def companion(title: str, back: str, template_name: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{escape(title)} | ReportKit prototype</title>
  <style>
    body{{margin:0;background:#edf2f7;color:#15233a;font:16px/1.5 "Segoe UI",Arial,sans-serif}}
    header{{background:#07192e;color:#fff;padding:24px}}main{{width:min(calc(100% - 36px),980px);margin:32px auto}}
    a{{color:#2875e2}}a:focus-visible{{outline:3px solid #66d0ff;outline-offset:3px}}
    .card{{background:#fff;border:1px solid #d6e0eb;border-radius:18px;padding:28px;box-shadow:0 15px 42px #14284812}}
    .label{{font-size:.75rem;font-weight:800;text-transform:uppercase;color:#607086}}h1{{margin:8px 0}}
    .notice{{margin-top:20px;padding:14px;border-left:4px solid #2875e2;background:#eaf3ff}}
    @media print{{body{{background:#fff}}.card{{box-shadow:none}}}}
  </style>
</head>
<body>
  <header><strong>ReportKit · {escape(template_name)} v1.0</strong></header>
  <main>
    <p><a href="{escape(back)}">← Back to overview</a></p>
    <article class="card">
      <p class="label">Static prototype companion</p>
      <h1>{escape(title)}</h1>
      <p>This page completes the approved prototype's static navigation contract. The deterministic
      generator will populate this page from canonical groups, items, metrics, and state definitions
      when this template is connected to the engine.</p>
      <p class="notice">No source-specific data or live behavior is embedded in this design artifact.</p>
    </article>
  </main>
</body>
</html>
"""


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "templates"
    aliases = {
        root / "portfolio-team" / "portfolio-team.html": root / "portfolio-team" / "prototype.html",
        root / "operational-health" / "operational-health.html": root / "operational-health" / "prototype.html",
        root / "compliance-readiness" / "compliance-readiness.html": root / "compliance-readiness" / "prototype.html",
    }
    for destination, source in aliases.items():
        destination.write_bytes(source.read_bytes())

    template_details = [
        ("portfolio-team", "Portfolio / Team", "portfolio-team.html"),
        ("operational-health", "Operational Health", "operational-health.html"),
        ("compliance-readiness", "Compliance / Readiness", "compliance-readiness.html"),
    ]
    for directory, template_name, back in template_details:
        prototype = (root / directory / "prototype.html").read_text(encoding="utf-8")
        links = sorted(set(re.findall(r'href="([^"]+\.html)"', prototype)))
        for link in links:
            destination = root / directory / link
            if destination.exists():
                continue
            title = PAGE_TITLES.get(link, Path(link).stem.replace("-", " ").title())
            destination.write_text(
                companion(title, back, template_name),
                encoding="utf-8",
                newline="\n",
            )
    print("Prototype companion pages are complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

