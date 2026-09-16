#!/usr/bin/env python3
"""Prepare public-safe prototype pages, interaction states, and the local showcase."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def normalize_prototype(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("static report template preview", "static report")
    text = text.replace("Classification Internal", "Classification Public sample")
    text = re.sub(r"\bInternal\b", "Public sample", text)
    if path.parent.name != "executive-health":
        text = text.replace("data-canonical=", "data-design-field=")
        text = text.replace("data-derived-from=", "data-design-derived-from=")
        text = text.replace(
            "Generated deterministically from canonical schema 1.0",
            "Approved hand-authored prototype · Illustrative values · Not generated from canonical data",
        )
        if "prototype-truth" not in text:
            text = text.replace(
                "</style>",
                ".prototype-truth{margin:0;background:#fff2d8;color:#704000;border-bottom:1px solid #e9c978;padding:10px 18px;text-align:center;font-weight:750;font-size:.82rem}</style>",
                1,
            )
            text = re.sub(
                r"(<body[^>]*>)",
                r"\1<div class=\"prototype-truth\" role=\"note\">Approved hand-authored design prototype · Values are illustrative and are not generated from the current canonical sample.</div>",
                text,
                count=1,
            )
    if path.parent.name == "action-risk":
        text = re.sub(
            r"https://example\.com/reportkit-sample/(?:actions|evidence)/([A-Za-z0-9-]+)",
            r"action-risk-reference.html#\1",
            text,
        )
        text = text.replace(' rel="external noopener"', "")
    if path.parent.name == "executive-health":
        text = re.sub(
            r'\s*<div class="preview-note" role="note">.*?</div>\s*',
            "\n",
            text,
            count=1,
            flags=re.DOTALL,
        )
        if 'class="status-meta"' not in text:
            text = text.replace(
                "</style>",
                ".status-meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:9px 16px;margin-top:14px;padding-top:13px;border-top:1px solid rgba(255,255,255,.14);color:#c8d5e3;font-size:.72rem}.status-meta strong{display:block;color:#fff}.status-meta .fresh{color:#8fe0bd}</style>",
                1,
            )
            text = re.sub(
                r'(<p class="status-copy">.*?</p>)',
                r'\1<div class="status-meta"><span>Report period<strong>Week ending 15 Sep 2026</strong></span><span class="fresh">Freshness<strong>Fresh · 5 min old</strong></span><span>Data as of<strong>15 Sep · 17:55 UTC</strong></span><span>Generated<strong>15 Sep · 18:00 UTC</strong></span></div>',
                text,
                count=1,
                flags=re.DOTALL,
            )
    if path.parent.name == "operational-health":
        text = text.replace(
            "<div><dt>Coverage</dt><dd>6 of 6 services</dd></div>",
            "<div><dt>Generated</dt><dd>15 Sept 2026, 18:00 UTC</dd></div>",
        )
    if path.parent.name == "compliance-readiness":
        text = text.replace(
            "<div><dt>Coverage</dt><dd>96 of 96 controls</dd></div>",
            "<div><dt>Generated</dt><dd>15 Sept 2026, 18:00 UTC</dd></div>",
        )
    path.write_text(text, encoding="utf-8", newline="\n")


def normalize_companion_metadata(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "Public sample" in text:
        return
    text = re.sub(
        r"(<header><strong>.*?</strong>)(</header>)",
        r"\1<p>Public sample · Period: Week ending 15 Sep 2026 · Freshness: Fresh · 5 min old · Data as of: 15 Sep 2026, 17:55 UTC · Generated: 15 Sep 2026, 18:00 UTC</p>\2",
        text,
        count=1,
        flags=re.DOTALL,
    )
    path.write_text(text, encoding="utf-8", newline="\n")


def action_reference() -> str:
    entries = [
        ("ACT-042", "Source item", "Rollback validation action record"),
        ("ACT-042-test-plan", "Test plan", "Synthetic rollback validation plan"),
        ("ACT-042-latest-run", "Latest run", "Synthetic validation-run evidence"),
        ("ACT-087", "Source item", "Certificate rotation action record"),
        ("ACT-087-rotation-log", "Rotation log", "Synthetic certificate rotation evidence"),
        ("ACT-103", "Source item", "Regional readiness action record"),
        ("ACT-103-coverage", "Coverage matrix", "Synthetic regional coverage evidence"),
        ("ACT-119", "Source item", "Telemetry retention action record"),
        ("ACT-119-package", "Exception package", "Synthetic exception evidence"),
        ("ACT-126", "Source item", "Dependency ownership action record"),
        ("ACT-138", "Source item", "Evidence archival action record"),
        ("ACT-138-closure", "Closure package", "Synthetic closure evidence"),
    ]
    sections = "".join(
        f'<section class="card" id="{escape(identifier)}"><p class="label">{escape(kind)}</p>'
        f'<h2>{escape(identifier)}</h2><p>{escape(description)}. This static reference contains '
        "no source-system connection or live data.</p></section>"
        for identifier, kind, description in entries
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Action reference | ReportKit prototype</title><style>
body{{margin:0;background:#edf2f7;color:#15233a;font:16px/1.5 "Segoe UI",Arial,sans-serif}}*{{box-sizing:border-box}}header{{background:#07192e;color:#fff;padding:24px}}main{{width:min(calc(100% - 36px),980px);margin:32px auto}}a{{color:#2875e2}}a:focus-visible{{outline:3px solid #66d0ff;outline-offset:3px}}.meta{{display:flex;gap:18px;flex-wrap:wrap;color:#c7d5e3;font-size:.78rem}}.card{{background:#fff;border:1px solid #d6e0eb;border-radius:18px;padding:24px;margin:16px 0;box-shadow:0 15px 42px #14284812}}.label{{font-size:.75rem;font-weight:800;text-transform:uppercase;color:#607086}}h1,h2{{margin:8px 0}}@media print{{body{{background:#fff}}.card{{box-shadow:none}}}}
</style></head><body><header><strong>ReportKit · Action &amp; Risk v1.0</strong><h1>Public sample action reference</h1><div class="meta"><span>Period: Week ending 15 Sep 2026</span><span>Freshness: Fresh · 5 min old</span><span>Data as of: 15 Sep · 17:55 UTC</span><span>Generated: 15 Sep · 18:00 UTC</span></div></header><main><p><a href="prototype.html">← Back to Action &amp; Risk prototype</a></p>{sections}</main></body></html>"""


def action_state(
    title: str,
    selected: str,
    rows: list[dict[str, str]],
    counts: dict[str, int],
) -> str:
    links = [
        ("All open", "action-risk.html", "all"),
        ("Overdue", "action-risk-overdue.html", "overdue"),
        ("Blocked", "action-risk-blocked.html", "blocked"),
        ("Due in 7 days", "action-risk-due-seven-days.html", "due"),
    ]
    tiles = "".join(
        f'<a class="tile{" selected" if key == selected else ""}" href="{href}" '
        f'aria-current="{"page" if key == selected else "false"}"><span>{escape(label)}</span>'
        f'<strong>{counts[key]}</strong></a>'
        for label, href, key in links
    )
    body = "".join(
        f"""<tr><td><strong>{escape(row['title'])}</strong><span>{escape(row['summary'])}</span></td>
        <td>{escape(row['accountable'])}<small>Action: {escape(row['action'])}</small></td>
        <td><strong>{escape(row['due'])}</strong><small>ETA {escape(row['eta'])}</small></td>
        <td><span class="status">{escape(row['status'])}</span><small>{escape(row['blocker'])}</small></td>
        <td>{escape(row['next'])}</td></tr>"""
        for row in rows
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(title)} | ReportKit</title><style>
:root{{--navy:#07192e;--ink:#14213a;--muted:#607086;--canvas:#edf2f7;--line:#d6e0eb;--red:#c83e4d;--blue:#2875e2}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--canvas);color:var(--ink);font:16px/1.5 "Segoe UI",Arial,sans-serif}}a{{color:inherit}}a:focus-visible{{outline:3px solid #66d0ff;outline-offset:3px}}header{{background:linear-gradient(140deg,var(--navy),#103154);color:#fff}}.shell{{width:min(calc(100% - 36px),1380px);margin:auto}}.mast{{min-height:76px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #ffffff25}}.brand{{font-weight:800}}.class{{border:1px solid #ffffff55;border-radius:99px;padding:6px 10px;font-size:.75rem;text-transform:uppercase}}.hero{{display:grid;grid-template-columns:1.1fr .9fr;gap:40px;padding:34px 0 44px;align-items:center}}h1{{font-size:clamp(2.5rem,5vw,4.2rem);line-height:1;margin:8px 0}}.eyebrow{{color:#66d0ff;font-size:.76rem;font-weight:800;text-transform:uppercase;letter-spacing:.12em}}.summary{{padding:20px;border:1px solid #ffffff30;border-radius:16px;background:#ffffff12}}.meta{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;color:#c7d5e3;font-size:.76rem}}main{{padding:22px 0 44px}}.tiles{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.tile{{display:block;background:#fff;border:1px solid var(--line);border-top:4px solid var(--blue);border-radius:15px;padding:18px;text-decoration:none;box-shadow:0 12px 30px #14284810}}.tile span{{display:block;color:var(--muted);font-weight:750}}.tile strong{{display:block;font-size:2rem;margin-top:5px}}.tile.selected{{border-color:var(--red);border-top-color:var(--red);box-shadow:0 0 0 3px #c83e4d25}}.queue{{margin-top:18px;background:#fff;border:1px solid var(--line);border-radius:18px;overflow:hidden}}.queue-head{{display:flex;justify-content:space-between;align-items:end;padding:22px}}.queue-head h2{{margin:0}}.queue-head p{{margin:4px 0 0;color:var(--muted)}}table{{width:100%;border-collapse:collapse}}th,td{{text-align:left;vertical-align:top;padding:14px;border-top:1px solid var(--line)}}th{{font-size:.7rem;text-transform:uppercase;color:var(--muted);background:#f7f9fb}}td span,td small{{display:block;color:var(--muted);margin-top:3px}}.status{{display:inline-block!important;background:#ffeaed;color:#a42d3d;border-radius:99px;padding:4px 8px;font-size:.7rem;font-weight:800}}footer{{display:flex;justify-content:space-between;padding:20px 0;color:var(--muted);font-size:.76rem}}
@media(max-width:800px){{.hero{{grid-template-columns:1fr}}.tiles{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:620px){{.tiles{{grid-template-columns:1fr}}table,tbody,tr,td{{display:block;width:100%}}thead{{position:absolute;width:1px;height:1px;overflow:hidden}}tr{{padding:10px;border-top:1px solid var(--line)}}td{{border:0;padding:7px}}footer{{display:grid}}}}
@media(prefers-reduced-motion:reduce){{*{{transition:none!important}}}}@media print{{body{{background:#fff}}.tile,.queue{{box-shadow:none}}}}
</style></head><body><div class="prototype-truth" role="note" style="margin:0;background:#fff2d8;color:#704000;border-bottom:1px solid #e9c978;padding:10px 18px;text-align:center;font-weight:750;font-size:.82rem">Approved design prototype populated from the public canonical sample · The production Action &amp; Risk renderer is not implemented.</div><header><div class="shell mast"><span class="brand">ReportKit · Action &amp; Risk v1.0</span><span class="class">Public sample</span></div><div class="shell hero"><div><p class="eyebrow">Operator action brief</p><h1>{escape(title)}</h1><p>Canonical sample rendered through the prototype design</p></div><section class="summary"><h2>Prototype state</h2><p><strong>{len(rows)} canonical records match this selection.</strong></p><div class="meta"><span>Period<br><strong>Week ending 15 Sep 2026</strong></span><span>Freshness<br><strong>Fresh · 5 min old</strong></span><span>Data as of<br><strong>15 Sep · 17:55 UTC</strong></span><span>Generated prototype<br><strong>15 Sep · 18:00 UTC</strong></span></div></section></div></header><main class="shell"><nav class="tiles" aria-label="Action queue filters">{tiles}</nav><section class="queue"><div class="queue-head"><div><h2>{escape(title)}</h2><p>Selected prototype filter: {escape(title)}</p></div><strong>{len(rows)} canonical records</strong></div><table><caption style="position:absolute;width:1px;height:1px;overflow:hidden">Canonical records in the prototype action queue</caption><thead><tr><th>Action</th><th>Ownership</th><th>Due / ETA</th><th>Status / blocker</th><th>Next action</th></tr></thead><tbody>{body}</tbody></table></section><footer><span>Prototype design · Facts from canonical-report.json</span><a href="action-risk.html">Reset to All attention</a></footer></main></body></html>"""


def portfolio_detail() -> str:
    rows = [
        ("Rollback validation", "Release Engineering", "Sample Owner 7", "12 Sep", "18 Sep", "Blocked", "Reserve test capacity"),
        ("Production-ring approval", "Platform Readiness", "Sample Owner 3", "14 Sep", "17 Sep", "At risk", "Confirm approval owner"),
        ("Regional evidence", "Cloud Readiness", "Sample Owner 9", "17 Sep", "19 Sep", "In progress", "Close two evidence gaps"),
    ]
    body = "".join(
        f"<tr><td><strong>{escape(title)}</strong></td><td>{escape(accountable)}<small>Action: {escape(action)}</small></td><td>{escape(due)}<small>ETA {escape(eta)}</small></td><td><span class=\"state\">{escape(status)}</span></td><td>{escape(next_action)}</td></tr>"
        for title, accountable, action, due, eta, status, next_action in rows
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Platform Readiness | ReportKit</title><style>
body{{margin:0;background:#edf2f7;color:#15233a;font:16px/1.5 "Segoe UI",Arial,sans-serif}}*{{box-sizing:border-box}}a{{color:#2875e2}}a:focus-visible{{outline:3px solid #66d0ff;outline-offset:3px}}header{{background:linear-gradient(140deg,#07192e,#103154);color:#fff}}.shell{{width:min(calc(100% - 36px),1320px);margin:auto}}.mast{{min-height:74px;display:flex;align-items:center;justify-content:space-between}}.hero{{padding:30px 0 40px}}h1{{font-size:3.6rem;line-height:1;margin:12px 0}}.class{{border:1px solid #ffffff55;border-radius:99px;padding:6px 10px;font-size:.75rem;text-transform:uppercase}}main{{padding:24px 0 44px}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.metric,.card{{background:#fff;border:1px solid #d6e0eb;border-radius:17px;box-shadow:0 14px 38px #14284812}}.metric{{padding:18px}}.metric strong{{display:block;font-size:2rem}}.metric span{{color:#607086;font-size:.76rem}}.card{{margin-top:16px;overflow:hidden}}.card h2,.card>p{{margin-left:22px;margin-right:22px}}table{{width:100%;border-collapse:collapse}}th,td{{padding:14px;text-align:left;border-top:1px solid #d6e0eb;vertical-align:top}}th{{background:#f7f9fb;color:#607086;font-size:.7rem;text-transform:uppercase}}small{{display:block;color:#607086}}.state{{display:inline-flex;padding:4px 8px;border-radius:99px;background:#ffeaed;color:#a42d3d;font-size:.72rem;font-weight:800;white-space:nowrap}}.meta{{display:flex;flex-wrap:wrap;gap:20px;color:#c7d5e3;font-size:.76rem}}@media(max-width:700px){{.metrics{{grid-template-columns:repeat(2,1fr)}}table,tbody,tr,td{{display:block}}thead{{position:absolute;width:1px;height:1px;overflow:hidden}}}}@media print{{body{{background:#fff}}.metric,.card{{box-shadow:none}}}}
</style></head><body><header><div class="shell mast"><strong>ReportKit · Portfolio / Team v1.0</strong><span class="class">Public sample</span></div><div class="shell hero"><a href="portfolio-team.html">← Back to portfolio</a><h1>Platform Readiness</h1><p>Team detail · strongest attention signal: constrained rollback validation</p><div class="meta"><span>Week ending 15 Sep 2026</span><span>Fresh · 5 min old</span><span>Data as of 15 Sep · 17:55 UTC</span><span>Generated 15 Sep · 18:00 UTC</span></div></div></header><main class="shell"><section class="metrics"><article class="metric"><strong>62</strong><span>raw records</span></article><article class="metric"><strong>12</strong><span>attention records</span></article><article class="metric"><strong>4</strong><span>management decisions</span></article><article class="metric"><strong>80.6%</strong><span>healthy</span></article></section><section class="card"><h2>Management intervention</h2><p>Secure reserved test capacity and confirm the rollback decision by 17 Sep.</p></section><section class="card"><h2>Team attention items</h2><table><thead><tr><th>Item</th><th>Ownership</th><th>Due / ETA</th><th>Status</th><th>Next action</th></tr></thead><tbody>{body}</tbody></table></section></main></body></html>"""


def showcase() -> str:
    cards = [
        ("Executive Health", "Do leaders need to intervene?", "../examples/operational-snapshot/generated/executive-health/index.html", "Generated end to end", "../docs/assets/screenshots/executive-health-hero.png"),
        ("Action & Risk", "What must happen next?", "../templates/action-risk/action-risk.html", "Approved prototype", "../docs/assets/screenshots/action-risk-hero.png"),
        ("Portfolio / Team", "Which teams carry the risk?", "../templates/portfolio-team/portfolio-team.html", "Approved prototype", "../docs/assets/screenshots/portfolio-team-hero.png"),
        ("Operational Health", "What regressed?", "../templates/operational-health/operational-health.html", "Approved prototype", "../docs/assets/screenshots/operational-health-hero.png"),
        ("Compliance / Readiness", "Can we proceed?", "../templates/compliance-readiness/compliance-readiness.html", "Approved prototype", "../docs/assets/screenshots/compliance-readiness-hero.png"),
    ]
    card_html = "".join(
        f'<a class="card" href="{href}"><img src="{image}" alt=""><div class="card-body"><span class="status">{escape(status)}</span><h2>{escape(name)}</h2><p>{escape(question)}</p><strong>Open report →</strong></div></a>'
        for name, question, href, status, image in cards
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ReportKit Showcase</title><style>
body{{margin:0;background:#edf2f7;color:#14213a;font:16px/1.5 "Segoe UI",Arial,sans-serif}}*{{box-sizing:border-box}}a{{color:inherit}}a:focus-visible{{outline:3px solid #66d0ff;outline-offset:4px}}header{{background:linear-gradient(140deg,#07192e,#103154);color:#fff;padding:70px 0}}.shell{{width:min(calc(100% - 36px),1200px);margin:auto}}.eyebrow{{color:#66d0ff;text-transform:uppercase;font-weight:800;letter-spacing:.12em}}h1{{font-size:clamp(3rem,7vw,6rem);line-height:.95;margin:12px 0;max-width:900px}}.lead{{color:#c5d4e3;font-size:1.2rem;max-width:760px}}.proof{{display:flex;gap:12px;flex-wrap:wrap;margin-top:25px}}.proof span{{border:1px solid #ffffff35;border-radius:99px;padding:8px 12px}}main{{padding:45px 0}}.grid{{display:grid;grid-template-columns:repeat(6,1fr);gap:16px}}.card{{grid-column:span 2;display:block;overflow:hidden;background:#fff;border:1px solid #d6e0eb;border-radius:18px;text-decoration:none;box-shadow:0 15px 42px #14284812}}.card:first-child,.card:nth-child(2){{grid-column:span 3}}.card img{{display:block;width:100%;aspect-ratio:1.44;object-fit:cover;object-position:top}}.card-body{{padding:22px}}.card h2{{font-size:1.45rem;margin:20px 0 5px}}.card p{{color:#607086}}.card strong{{color:#2875e2}}.status{{display:inline-flex;padding:5px 9px;border-radius:99px;background:#eaf3ff;color:#225f9f;font-size:.7rem;font-weight:800;text-transform:uppercase}}.boundary,.sample{{margin-top:28px;padding:28px;border-radius:18px}}.boundary{{background:#07192e;color:#fff}}.boundary strong{{display:block;font-size:1.2rem;margin:7px 0}}.sample{{background:#fff;border:1px solid #d6e0eb}}.sample a{{color:#2875e2;font-weight:800}}footer{{padding:28px 0;color:#607086}}@media(max-width:750px){{.grid{{grid-template-columns:1fr}}.card,.card:first-child,.card:nth-child(2){{grid-column:auto}}}}
</style></head><body><header><div class="shell"><p class="eyebrow">Open-source Hack Week project</p><h1>Turn operational data into decision-ready static reports.</h1><p class="lead">One model. Five report designs. One generated today.</p><div class="proof"><span>Executive Health renderer</span><span>Four design prototypes</span><span>Static-first</span><span>Validation baseline</span></div></div></header><main class="shell"><div class="grid">{card_html}</div><section class="sample"><h2>Bring your own template</h2><p>Project-local declarative packs compose approved components without executable template code.</p><p><span class="status">Project template · declarative</span></p><a href="../examples/custom-template-project/generated/release-review/index.html">Open the Release Review example →</a></section><section class="sample"><h2>Inspect the generated facts</h2><p>The Executive Health renderer uses this public synthetic canonical snapshot. The other four cards are explicitly illustrative design prototypes.</p><a href="../examples/operational-snapshot/canonical-report.json">Open the 401-record canonical sample →</a></section><section class="boundary"><span>Product boundary</span><strong>The source determines the facts.</strong><strong>The template determines how those facts are communicated.</strong><strong>The destination determines where the generated report lives.</strong></section></main><footer class="shell">ReportKit · Experimental local showcase · No publication performed</footer></body></html>"""


def social_preview() -> str:
    return """<!doctype html><html><head><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;width:1200px;height:630px;overflow:hidden;background:linear-gradient(135deg,#07192e,#12395f);color:#fff;font:22px/1.25 "Segoe UI",Arial,sans-serif}.wrap{padding:54px}.eyebrow{color:#66d0ff;text-transform:uppercase;font-size:16px;font-weight:800;letter-spacing:.14em}h1{font-size:62px;line-height:.98;margin:13px 0 14px;max-width:800px}.sub{color:#c6d5e4}.screens{position:absolute;right:45px;bottom:42px;width:500px;height:310px}.screens img{position:absolute;width:330px;border:5px solid #fff;border-radius:12px;box-shadow:0 18px 50px #0008}.screens img:nth-child(1){right:78px;top:0;z-index:3}.screens img:nth-child(2){left:0;bottom:0;transform:rotate(-5deg)}.screens img:nth-child(3){right:0;bottom:0;transform:rotate(5deg)}.footer{position:absolute;left:54px;bottom:55px;font-weight:700}.footer span{margin-right:24px}</style></head><body><div class="wrap"><p class="eyebrow">ReportKit</p><h1>One model.<br>Five report designs.<br>One generated today.</h1><p class="sub">Executive Health generated · Four approved prototypes</p><div class="screens"><img src="../docs/assets/screenshots/executive-health-hero.png"><img src="../docs/assets/screenshots/action-risk-hero.png"><img src="../docs/assets/screenshots/portfolio-team-hero.png"></div><div class="footer"><span>Open source</span><span>Static-first</span><span>Validation baseline</span></div></div></body></html>"""


def presentation_title() -> str:
    return """<!doctype html><html><head><meta charset="utf-8"><style>*{box-sizing:border-box}body{margin:0;width:1920px;height:1080px;overflow:hidden;background:linear-gradient(135deg,#07192e,#0e3155);color:#fff;font:28px/1.3 "Segoe UI",Arial,sans-serif}.wrap{padding:100px}.eyebrow{color:#66d0ff;text-transform:uppercase;font-size:20px;font-weight:800;letter-spacing:.15em}h1{font-size:108px;line-height:.95;margin:24px 0;max-width:1250px}.lead{color:#c5d4e3;font-size:34px;max-width:1100px}.proof{display:flex;gap:18px;margin-top:48px}.proof span{border:1px solid #ffffff45;border-radius:99px;padding:12px 18px}.shot{position:absolute;right:90px;bottom:70px;width:680px;border:7px solid #fff;border-radius:20px;box-shadow:0 30px 80px #0008}</style></head><body><div class="wrap"><p class="eyebrow">ReportKit · Experimental Hack Week preview</p><h1>Turn operational data into decision-ready static reports.</h1><p class="lead">One generated report. Four approved prototypes. No backend.</p><div class="proof"><span>Skill-first</span><span>Deterministic</span><span>Validation baseline</span></div><img class="shot" src="../docs/assets/screenshots/executive-health-hero.png"></div></body></html>"""


def walkthrough() -> str:
    slides = [
        ("The leadership view", "Do leaders need to intervene?", "../docs/assets/screenshots/executive-health-hero.png"),
        ("The operator view", "What must happen next?", "../docs/assets/screenshots/action-risk-hero.png"),
        ("The manager view", "Which teams carry the risk?", "../docs/assets/screenshots/portfolio-team-hero.png"),
        ("The reliability view", "What regressed?", "../docs/assets/screenshots/operational-health-hero.png"),
        ("The assurance view", "Can we proceed?", "../docs/assets/screenshots/compliance-readiness-hero.png"),
    ]
    content = "".join(
        f'<section class="slide"><div><p>One model · Five designs · One generated today</p><h1>{escape(title)}</h1><h2>{escape(question)}</h2></div><img src="{image}"></section>'
        for title, question, image in slides
    )
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>*{{box-sizing:border-box}}body{{margin:0;width:1280px;height:720px;overflow:hidden;background:#07192e;color:#fff;font:20px/1.3 "Segoe UI",Arial,sans-serif}}.slide{{position:absolute;inset:0;display:grid;grid-template-columns:390px 1fr;gap:34px;align-items:center;padding:45px;opacity:0;animation:show 35s linear infinite}}.slide:nth-child(1){{animation-delay:0s}}.slide:nth-child(2){{animation-delay:7s}}.slide:nth-child(3){{animation-delay:14s}}.slide:nth-child(4){{animation-delay:21s}}.slide:nth-child(5){{animation-delay:28s}}.slide p{{color:#66d0ff;text-transform:uppercase;font-size:14px;font-weight:800;letter-spacing:.13em}}h1{{font-size:54px;line-height:1;margin:14px 0}}h2{{color:#c5d4e3;font-size:24px;font-weight:500}}img{{width:100%;border:5px solid #fff;border-radius:16px;box-shadow:0 24px 60px #0008}}@keyframes show{{0%,19%{{opacity:1}}20%,100%{{opacity:0}}}}</style></head><body>{content}</body></html>"""


def main() -> int:
    for template in ("executive-health", "action-risk", "portfolio-team", "operational-health", "compliance-readiness"):
        normalize_prototype(TEMPLATES / template / "prototype.html")

    aliases = {
        TEMPLATES / "action-risk" / "action-risk.html": TEMPLATES / "action-risk" / "prototype.html",
        TEMPLATES / "portfolio-team" / "portfolio-team.html": TEMPLATES / "portfolio-team" / "prototype.html",
        TEMPLATES / "operational-health" / "operational-health.html": TEMPLATES / "operational-health" / "prototype.html",
        TEMPLATES / "compliance-readiness" / "compliance-readiness.html": TEMPLATES / "compliance-readiness" / "prototype.html",
    }
    for destination, source in aliases.items():
        destination.write_bytes(source.read_bytes())

    canonical = json.loads(
        (ROOT / "examples" / "operational-snapshot" / "canonical-report.json").read_text(encoding="utf-8")
    )
    report_date = datetime.fromisoformat(canonical["report"]["generatedAt"].replace("Z", "+00:00")).date()
    due_limit = report_date + timedelta(days=7)
    attention_items = [
        item for item in canonical["items"]
        if item.get("status") in {"warning", "critical"}
    ]

    def owner_label(value: object) -> str:
        if not isinstance(value, dict):
            return "Unassigned"
        return str(value.get("displayName") or value.get("team") or value.get("id") or "Unassigned")

    def date_label(value: object) -> str:
        if not isinstance(value, str):
            return "Not set"
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d %b")

    def action_row(item: dict[str, object]) -> dict[str, str]:
        return {
            "title": str(item["title"]),
            "summary": str(item.get("summary", "")),
            "accountable": owner_label(item.get("accountableOwner")),
            "action": owner_label(item.get("actionOwner")),
            "due": date_label(item.get("dueDate")),
            "eta": date_label(item.get("eta")),
            "status": str(item.get("statusText") or item["status"]).replace("-", " ").title(),
            "blocker": str(item.get("blocker") or "No blocker recorded"),
            "next": str(item.get("nextAction") or "No next action recorded"),
        }

    selected = {
        "all": attention_items,
        "overdue": [
            item for item in attention_items
            if isinstance(item.get("dueDate"), str) and date.fromisoformat(str(item["dueDate"])) < report_date
        ],
        "blocked": [item for item in attention_items if item.get("blocker")],
        "due": [
            item for item in attention_items
            if isinstance(item.get("dueDate"), str)
            and report_date <= date.fromisoformat(str(item["dueDate"])) <= due_limit
        ],
    }
    counts = {key: len(value) for key, value in selected.items()}
    action_dir = TEMPLATES / "action-risk"
    (action_dir / "action-risk-reference.html").write_text(
        action_reference(), encoding="utf-8", newline="\n"
    )
    states = {
        "action-risk.html": ("All attention records", "all"),
        "action-risk-overdue.html": ("Overdue attention records", "overdue"),
        "action-risk-blocked.html": ("Blocked attention records", "blocked"),
        "action-risk-due-seven-days.html": ("Attention records due in seven days", "due"),
    }
    for name, (title, selection) in states.items():
        rows = [action_row(item) for item in selected[selection]]
        (action_dir / name).write_text(
            action_state(title, selection, rows, counts),
            encoding="utf-8",
            newline="\n",
        )

    (TEMPLATES / "portfolio-team" / "portfolio-team-platform-readiness.html").write_text(
        portfolio_detail(), encoding="utf-8", newline="\n"
    )
    for page in TEMPLATES.rglob("*.html"):
        normalize_companion_metadata(page)
    showcase_dir = ROOT / "showcase"
    showcase_dir.mkdir(exist_ok=True)
    (showcase_dir / "index.html").write_text(showcase(), encoding="utf-8", newline="\n")
    (showcase_dir / "social-preview.html").write_text(social_preview(), encoding="utf-8", newline="\n")
    (showcase_dir / "presentation-title.html").write_text(presentation_title(), encoding="utf-8", newline="\n")
    (showcase_dir / "walkthrough.html").write_text(walkthrough(), encoding="utf-8", newline="\n")
    print("Prepared public marketing pages and showcase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
