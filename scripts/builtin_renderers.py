"""Static, source-independent audience views of the canonical ReportKit model.

Group ``page`` hints never name output files. Portfolio navigation uses the full
SHA-256 of the canonical group ID; source URLs are text references, not links.
Rendering reads neither files, the network, nor the current clock.
"""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
from html import escape
import math
import re
from urllib.parse import urlsplit


_CSP = (
    "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; "
    "font-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; form-action 'none'"
)
_ATTENTION = {
    "warning", "critical", "blocked", "failed", "in-progress",
    "pending-review", "not-started",
}
_RESOLVED = {"healthy", "passed", "complete", "not-applicable"}
_STATUS = _ATTENTION | _RESOLVED | {"unknown"}
_PRIORITY = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
_TITLES = {
    "action-risk": "Action & Risk",
    "portfolio-team": "Portfolio / Team",
    "operational-health": "Operational Health",
    "compliance-readiness": "Compliance / Readiness",
}

_CSS = """
:root{--navy:#07192e;--ink:#14213a;--muted:#526277;--canvas:#edf2f7;--line:#d6e0eb;
--accent:#2865bb;--surface:#fff;--soft:#eaf1fb}
*{box-sizing:border-box}body{margin:0;background:var(--canvas);color:var(--ink);
font:16px/1.55 "Segoe UI",Arial,sans-serif}a{color:#17579b;text-underline-offset:3px}
a:hover{text-decoration-thickness:2px}a:focus-visible,summary:focus-visible{
outline:3px solid #248bc2;outline-offset:4px}p{margin:.45rem 0 1rem}
h1,h2,h3{line-height:1.18;overflow-wrap:anywhere}h1{font-size:clamp(2rem,4.8vw,3.9rem);
letter-spacing:-.04em;margin:.4rem 0 1rem}h2{font-size:1.5rem;margin:0 0 1rem}
h3{font-size:1.12rem;margin:.35rem 0 .75rem}.shell{width:min(1400px,calc(100% - 48px));margin:auto}
.skip{position:fixed;top:8px;left:8px;transform:translateY(-200%);z-index:10;
background:white;padding:10px}.skip:focus{transform:none}header{color:white;
background:linear-gradient(130deg,var(--navy),#173958)}.mast{display:flex;gap:20px;
justify-content:space-between;align-items:center;min-height:72px;border-bottom:1px solid #ffffff33}
.brand{font-weight:800;letter-spacing:.025em}.classification{font-size:.8rem;
border:1px solid currentColor;border-radius:99px;padding:5px 12px}.hero{display:grid;
grid-template-columns:1.5fr 1fr;gap:40px;padding:36px 0}.eyebrow{text-transform:uppercase;
letter-spacing:.13em;font-size:.76rem;font-weight:800;color:#afd8fb}.subtitle{color:#d6e2ed}
.report-status{padding:22px;background:#ffffff10;border:1px solid #ffffff33;border-radius:14px}
.report-status h2{margin:.4rem 0}.metadata{display:grid;grid-template-columns:1fr 1fr;gap:12px;
font-size:.78rem}.metadata strong{display:block}.freshness{font-weight:700}
.freshness.critical{color:#ffccd2}.freshness.warning{color:#ffe0a8}
.freshness.fresh{color:#b1ebd3}.nav{display:flex;flex-wrap:wrap;gap:8px;padding:16px 0}
.nav a{border:1px solid var(--line);padding:9px 14px;border-radius:8px;background:white;
font-size:.88rem;font-weight:650;text-decoration:none}.nav a[aria-current=page]{
background:var(--accent);color:white;border-color:var(--accent)}main{padding:14px 0 32px}
section{margin-bottom:24px}.section-heading{display:flex;align-items:baseline;gap:18px;
justify-content:space-between;flex-wrap:wrap}.muted,.section-copy{color:var(--muted)}
.section-copy{font-size:.9rem}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));
gap:16px}.grid>*{min-width:0}.card{padding:23px;border:1px solid var(--line);background:white;
border-radius:15px;box-shadow:0 6px 22px #14284808}.metric{border-top:4px solid var(--accent)}
.metric-value{font-size:2.3rem;font-weight:800;line-height:1.15;overflow-wrap:anywhere}
.unit{font-size:.82rem;color:var(--muted);font-weight:600}.metric dl{font-size:.84rem}
.badge{display:inline-block;padding:3px 8px;border-radius:99px;background:#e9eef4;color:#354459;
font-weight:700;font-size:.72rem;letter-spacing:.02em;text-transform:uppercase}
.badge-warning,.badge-in-progress,.badge-pending-review{background:#fff0ce;color:#7a4500}
.badge-critical,.badge-blocked,.badge-failed{background:#ffe7eb;color:#9f2439}
.badge-healthy,.badge-passed,.badge-complete{background:#e2f4eb;color:#146046}
.badge-not-started{background:#ebe6f9;color:#593986}.badge-not-applicable{background:#eee;color:#505050}
.empty{padding:18px;background:#f5f7fa;border:1px dashed #a9b6c6;border-radius:9px;color:#4c5b6e}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}
.stat{display:block;padding:18px 20px;background:white;border:1px solid var(--line);
border-left:4px solid var(--accent);border-radius:10px;text-decoration:none;color:var(--ink)}
.stat strong{display:block;font-size:2.1rem;line-height:1.25}.stat span{font-size:.85rem}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;background:white}
table{width:100%;border-collapse:collapse;font-size:.86rem}caption{text-align:left;
padding:16px 18px;font-weight:700;background:var(--soft)}th,td{text-align:left;vertical-align:top;
padding:15px;border-top:1px solid var(--line);overflow-wrap:anywhere}th{background:#f5f7fa;
font-size:.75rem;text-transform:uppercase;letter-spacing:.03em}td:first-child{min-width:200px}
td{min-width:155px}.records th:first-child{width:28%}.records td dl{margin:8px 0}
dt{font-size:.73rem;font-weight:700;color:var(--muted)}dd{margin:0 0 9px;overflow-wrap:anywhere}
.record-id{display:block;font-size:.7rem;color:var(--muted);margin:6px 0}.links{padding-left:19px;
margin:8px 0}.links li{margin:5px 0}.group-card{border-top:4px solid var(--accent)}
.reference-url{display:block;color:var(--muted);font-size:.78rem;overflow-wrap:anywhere}
.group-link{display:block;font-size:1.2rem;font-weight:800;margin:4px 0 12px}
.group-count{font-size:1.8rem;font-weight:800}.membership{font-size:.83rem;margin-top:12px}
.signals{display:grid;gap:12px;padding:0;list-style:none}.signals li{padding:18px;
border-left:4px solid var(--accent);background:white;border-radius:0 10px 10px 0}
.signals h3{display:inline;margin-left:8px}.signal-refs{font-size:.8rem}
.trend-card{min-width:0}.chart{width:100%;height:160px;display:block;color:var(--accent)}
.chart .baseline{stroke:#718298;stroke-dasharray:4 4}.chart .series{stroke:currentColor;
stroke-width:3;fill:none}.chart .point{fill:currentColor;stroke:white;stroke-width:1}
.trend-card table{font-size:.78rem}.trend-card td,.trend-card th{min-width:0;padding:7px 10px}
.trend-card caption{padding:8px 10px}.trend-card .table-wrap{margin-top:12px}
.appendix{padding:18px;border:1px solid var(--line);background:white;border-radius:12px;margin:24px 0}
summary{cursor:pointer;font-weight:700}details[open]>summary{margin-bottom:16px}
.requirement{margin:12px 0;border:1px solid var(--line);border-left:5px solid var(--accent);
border-radius:10px;background:white;padding:18px 22px}.requirement summary{display:list-item}
.requirement summary .badge{margin-right:12px}.requirement-grid{display:grid;
grid-template-columns:repeat(3,minmax(0,1fr));gap:22px;margin-top:18px}.requirement h3{
font-size:.8rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}
.gate-list{list-style:none;padding:0;display:grid;gap:10px}.gate-list li{
display:flex;gap:20px;align-items:center;background:white;border:1px solid var(--line);
border-radius:10px;padding:16px 20px;justify-content:space-between}.gate-list strong{display:block}
.notice{padding:18px 22px;border-left:4px solid var(--accent);background:var(--soft)}
.two-column{display:grid;grid-template-columns:1.4fr 1fr;gap:22px}
footer{border-top:1px solid var(--line);padding:24px 0;color:var(--muted);font-size:.78rem}
footer dl{display:flex;flex-wrap:wrap;gap:24px}footer .freshness{color:var(--ink)}
.action-risk{--accent:#b3334a;--soft:#fff0f2}.action-risk header{
background:linear-gradient(125deg,#141c30,#342136)}.action-risk .stats{position:relative}
.action-risk .records td:first-child{border-left:3px solid var(--accent)}
.portfolio-team{--accent:#6842a1;--soft:#f2ecfa}.portfolio-team header{
background:linear-gradient(125deg,#131e35,#3a2854)}.portfolio-team .group-card{padding:28px}
.portfolio-team .group-link{font-size:1.35rem}.portfolio-team .group-count{color:var(--accent)}
.operational-health{--accent:#096e78;--soft:#e8f5f5;--canvas:#eef4f5}
.operational-health header{background:linear-gradient(125deg,#071e29,#103b42)}
.operational-health .metric{border-radius:8px}.operational-health .metric-value{
font-variant-numeric:tabular-nums}.operational-health .trend-card{border-radius:8px}
.compliance-readiness{--accent:#865319;--soft:#faf2e5;--canvas:#f6f4ef}
.compliance-readiness header{background:linear-gradient(125deg,#182333,#40352a)}
.compliance-readiness .card{border-radius:8px}.compliance-readiness h2{letter-spacing:-.025em}
@media(max-width:900px){.hero,.two-column{grid-template-columns:1fr}.hero{gap:20px}
.requirement-grid{grid-template-columns:1fr}.records{min-width:800px}}
@media(max-width:600px){.shell{width:calc(100% - 28px)}.mast{align-items:flex-start;padding:16px 0;
flex-direction:column;gap:8px}.metadata{grid-template-columns:1fr}.card{padding:18px}
.hero{padding:26px 0}.nav a{flex:1;text-align:center}.stats{grid-template-columns:1fr 1fr}
.gate-list li{align-items:flex-start;flex-direction:column;gap:8px}}
@media print{@page{margin:15mm}body{background:white;color:#111;font-size:10pt}
.shell{width:100%}header{background:white!important;color:#111;border-bottom:2px solid #111}
.eyebrow,.subtitle,.metadata,.freshness{color:#333!important}.hero{padding:18px 0;gap:18px}
h1{font-size:26pt}.mast{min-height:40px}.report-status{border:1px solid #777;padding:12px}
.card,.stat,.requirement,.signals li{box-shadow:none;break-inside:avoid;border-color:#bbb}
.nav,.skip{display:none}.table-wrap{overflow:visible}.records{min-width:0;font-size:8pt}
td,th{min-width:0!important;padding:7px}.records td:first-child{min-width:0}.grid{
grid-template-columns:repeat(2,minmax(0,1fr))}.table-wrap{border-radius:0}
thead{display:table-header-group}tr{break-inside:avoid}a{color:#111}.appendix{break-inside:auto}
.requirement-grid{grid-template-columns:repeat(3,minmax(0,1fr))}.chart{height:120px}
}
"""


def _text(value, fallback: str = "Not supplied") -> str:
    return escape(str(value)) if value is not None and value != "" else escape(fallback)


def _ordered(entries: list[dict]) -> list[dict]:
    return sorted(entries, key=lambda entry: (entry.get("order", 9999), str(entry.get("id", ""))))


def _has_blocker(item: dict) -> bool:
    return bool(str(item.get("blocker") or "").strip())


def _item_order(item: dict) -> tuple:
    return (
        _PRIORITY.get(item.get("priority"), 4), not _has_blocker(item),
        item.get("dueDate") or "9999-12-31", str(item.get("id", "")),
    )


def _key(prefix: str, identifier: str) -> str:
    return prefix + "-" + sha256(str(identifier).encode("utf-8")).hexdigest()


def _badge(status: str | None) -> str:
    status = status or "unknown"
    css = status if status in _STATUS else "unknown"
    return f'<span class="badge badge-{css}">{_text(status)}</span>'


def _owner(owner: dict | None) -> str:
    if not owner:
        return "Unknown / not supplied"
    return " · ".join(
        f"{label}: {_text(owner[key])}"
        for key, label in (("displayName", "Name"), ("alias", "Alias"), ("team", "Team"))
        if owner.get(key)
    ) or "Unknown / not supplied"


def _fields(pairs: list[tuple[str, str]]) -> str:
    return "<dl>" + "".join(f"<dt>{escape(label)}</dt><dd>{value}</dd>" for label, value in pairs) + "</dl>"


def _empty(message: str) -> str:
    return f'<p class="empty">{escape(message)}</p>'


def _instant(value: str | None) -> datetime | None:
    try:
        instant = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return instant.astimezone(timezone.utc) if instant.tzinfo else None
    except (ValueError, TypeError):
        return None


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except (ValueError, TypeError):
        return None


def _display_instant(value: str | None) -> str:
    from reportkit_engine import _format_datetime

    if value is None or _instant(value) is None:
        return "Not supplied"
    return escape(_format_datetime(value))


def _freshness(report: dict, config: dict) -> tuple[str, str]:
    generated, data_as_of = _instant(report.get("generatedAt")), _instant(report.get("dataAsOf"))
    if generated is None or data_as_of is None:
        return "unknown", "Freshness unknown: timestamps not supplied or invalid"
    minutes = int((generated - data_as_of).total_seconds() // 60)
    if minutes < 0:
        return "unknown", "Freshness unknown: dataAsOf is later than generatedAt"
    limits = config.get("freshnessThresholdsMinutes", {})
    if minutes <= limits.get("fresh", 60):
        return "fresh", f"Fresh · {minutes} min old"
    if minutes <= limits.get("stale", 1440):
        return "warning", f"Aging · {minutes} min old"
    return "critical", f"Stale · {minutes} min old"


class _Renderer:
    def __init__(self, template_id: str, model: dict, config: dict):
        self.template_id, self.model, self.config = template_id, model, config
        self.items = sorted(model.get("items", []), key=_item_order)
        self.groups = _ordered(model.get("groups", []))
        self.group_by_id = {group["id"]: group for group in self.groups}
        self.metric_by_id = {metric["id"]: metric for metric in model.get("metrics", [])}
        self.group_pages = {
            group["id"]: _key("group", group["id"]) + ".html" for group in self.groups
        } if template_id == "portfolio-team" else {}
        self.all_items_page = "all-records.html" if template_id in {"action-risk", "portfolio-team"} else "index.html"
        self.pages = {"index.html", self.all_items_page, *self.group_pages.values()}
        if template_id == "action-risk":
            self.pages.update({"overdue.html", "blocked.html", "due-next-seven-days.html"})
        self.members = {group["id"]: self._membership(group["id"]) for group in self.groups}

    def _membership(self, group_id: str) -> set[str]:
        seen, members, pending = set(), set(), [group_id]
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            group = self.group_by_id.get(current, {})
            members.update(group.get("itemIds", []))
            members.update(item["id"] for item in self.items if current in item.get("groupIds", []))
            pending.extend(group.get("childGroupIds", []))
        return members & {item["id"] for item in self.items}

    def _link(self, link: dict) -> str:
        label = _text(link.get("label"), "Unnamed link")
        destination = link.get("href") or link.get("page") or ""
        try:
            parsed = urlsplit(destination)
            external = (
                parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)
                and not any(ord(character) < 32 or ord(character) == 127 for character in destination)
                and "\\" not in destination
            )
        except ValueError:
            external = False
        if external:
            return (
                f'<span class="external-reference">{label}'
                f'<span class="reference-url">{escape(destination)}</span></span>'
            )
        if destination in self.pages:
            return f'<a href="{escape(destination, quote=True)}">{label}</a>'
        return f'<span>{label} <span class="muted">(destination unavailable in this report)</span></span>'

    def _links(self, links: list[dict] | None, missing: str = "No source links supplied.") -> str:
        if not links:
            return f'<span class="muted">{escape(missing)}</span>'
        return '<ul class="links">' + "".join(f"<li>{self._link(link)}</li>" for link in links) + "</ul>"

    def _item_link(self, item: dict) -> str:
        destination = self.all_items_page + "#" + _key("item", item["id"])
        return f'<a href="{destination}">{_text(item.get("title"))}</a>'

    def _group_link(self, group: dict, card: bool = False) -> str:
        destination = self.group_pages.get(group["id"], "index.html#" + _key("group", group["id"]))
        css = ' class="group-link"' if card else ""
        return (
            f'<a{css} data-group-id="{_text(group["id"])}" href="{destination}">'
            f'{_text(group.get("label"))}</a>'
        )

    def _item_groups(self, item: dict) -> str:
        groups = [group for group in self.groups if item["id"] in self.members[group["id"]]]
        return ", ".join(self._group_link(group) for group in groups) or "Ungrouped — no supplied group membership"

    def _record_sections(self, item: dict) -> tuple[str, str, str, str]:
        status = _fields([
            ("Status", _badge(item.get("status"))),
            ("Lifecycle", _text(item.get("lifecycle"), "Not supplied")),
            ("Category", _text(item.get("category"), "Not supplied")),
            ("Status detail", _text(item.get("statusText"), "Not supplied")),
            ("Priority", _text(item.get("priority"), "unknown")),
            ("Severity", _text(item.get("severity"), "unknown")),
            ("Confidence", _text(item.get("confidence"), "unknown")),
            ("Root-cause state", _text(item.get("rootCauseState"), "unknown")),
        ])
        ownership = _fields([
            ("Accountable owner", _owner(item.get("accountableOwner"))),
            ("Action owner", _owner(item.get("actionOwner"))),
            ("Due date", _text(item.get("dueDate"))),
            ("ETA", _text(item.get("eta"))),
            ("ETA health", _text(item.get("etaHealth"), "unknown")),
            ("Age", f'{_text(item.get("ageDays"))} days' if item.get("ageDays") is not None else "Unknown / not supplied"),
        ])
        action = _fields([
            ("Next action", _text(item.get("nextAction"), "Unknown / not supplied")),
            ("Next action date", _text(item.get("nextActionDate"))),
            ("Blocker", _text(item.get("blocker"), "Not supplied")),
        ])
        evidence = _fields([
            ("Evidence state", _text(item.get("evidenceState"), "unknown")),
            ("Exception state", _text((item.get("exception") or {}).get("status"), "Not supplied")),
            ("Exception expiry", _text((item.get("exception") or {}).get("expiresAt"), "Not supplied")),
            ("Readiness gate", _text((item.get("readinessGate") or {}).get("status"), "Not supplied")),
            ("Readiness decision", _text((item.get("readinessGate") or {}).get("decision"), "Not supplied")),
            ("Source links", self._links(item.get("links"))),
            ("Evidence", self._links(item.get("evidence"), "Unknown — no evidence supplied.")),
        ])
        return status, ownership, action, evidence

    def records(self, items: list[dict], caption: str, compliance: bool = False) -> str:
        if not items:
            return _empty("No records in this selection. No actions or approvals are inferred.")
        rows = []
        for item in items:
            status, ownership, action, evidence = self._record_sections(item)
            identity = (
                f'<strong>{_text(item.get("title"))}</strong>'
                f'<span class="record-id">ID: {_text(item["id"])}</span>'
                f'<p>{_text(item.get("summary"), "Summary not supplied.")}</p>'
                f'<p class="membership">{self._item_groups(item)}</p>'
            )
            attributes = f'id="{_key("item", item["id"])}" data-item-id="{_text(item["id"])}"'
            if compliance:
                rows.append(
                    f'<details class="requirement" {attributes} open><summary>{_badge(item.get("status"))} '
                    f'{_text(item.get("title"))}</summary>{identity}<div class="requirement-grid">'
                    f'<div><h3>Requirement assessment</h3>{status}{action}</div>'
                    f'<div><h3>Ownership and timing</h3>{ownership}</div>'
                    f'<div><h3>Evidence and traceability</h3>{evidence}</div></div></details>'
                )
            else:
                rows.append(
                    f'<tr {attributes}><td>{identity}</td><td>{status}</td>'
                    f'<td>{ownership}</td><td>{action}{evidence}</td></tr>'
                )
        if compliance:
            return "".join(rows)
        return (
            f'<div class="table-wrap" role="region" aria-label="{escape(caption)}" tabindex="0">'
            f'<table class="records"><caption>{escape(caption)} · {len(items)} records</caption>'
            '<thead><tr><th scope="col">Record / membership</th><th scope="col">Assessment</th>'
            '<th scope="col">Ownership / timing</th><th scope="col">Next action / evidence</th>'
            "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
        )

    def metrics(self, metrics: list[dict] | None = None) -> str:
        entries = _ordered(self.model.get("metrics", []) if metrics is None else metrics)
        cards = []
        for metric in entries:
            delta = metric.get("delta")
            delta_html = "Not supplied"
            if delta:
                delta_html = (
                    f'{_text(delta.get("value"))} {_text(delta.get("unit"), "unit not supplied")}'
                    + _fields([
                        ("Delta direction", _text(delta.get("direction"), "unknown")),
                        ("Delta assessment", _text(delta.get("assessment"), "unknown")),
                        ("Delta label", _text(delta.get("label"))),
                    ])
                )
            cards.append(
                f'<article class="card metric" data-metric-id="{_text(metric["id"])}">'
                f'<h3>{_text(metric.get("label"))}</h3>{_badge(metric.get("status"))}'
                f'<p class="metric-value">{_text(metric.get("value"))}</p>'
                f'<p class="unit">{_text(metric.get("unit"), "Unit not supplied")}</p>'
                f'<p class="section-copy">{_text(metric.get("description"), "Description not supplied.")}</p>'
                + _fields([
                    ("Target", f'{_text(metric["target"])} {_text(metric.get("unit"))}' if metric.get("target") is not None else "Not supplied"),
                    ("Delta", delta_html),
                ])
                + (self._link(metric["link"]) if metric.get("link") else '<span class="muted">No metric link supplied.</span>')
                + "</article>"
            )
        return '<div class="grid">' + "".join(cards) + "</div>" if cards else _empty("No metrics supplied.")

    def group_cards(self, groups: list[dict] | None = None) -> str:
        entries = self.groups if groups is None else groups
        cards = []
        for group in entries:
            members = [item for item in self.items if item["id"] in self.members[group["id"]]]
            metrics = [self.metric_by_id[key] for key in group.get("metricIds", []) if key in self.metric_by_id]
            metric_refs = "".join(
                f'<li>{_text(metric["label"])}: <strong>{_text(metric["value"])}</strong> '
                f'{_text(metric["unit"])} {_badge(metric.get("status"))}</li>' for metric in _ordered(metrics)
            )
            children = [self.group_by_id[key] for key in group.get("childGroupIds", []) if key in self.group_by_id]
            heading = self._group_link(group, True) if self.group_pages else f'<h3>{_text(group.get("label"))}</h3>'
            cards.append(
                f'<article class="card group-card" id="{_key("group", group["id"])}">'
                f'<p class="eyebrow muted">{_text(group.get("type"), "Group")}</p>{heading}'
                f'{_badge(group.get("status"))}<p>{_text(group.get("summary"), "Summary not supplied.")}</p>'
                f'<p><span class="group-count">{len(members)}</span> distinct member records</p>'
                + _fields([
                    ("Accountable owner", _owner(group.get("accountableOwner"))),
                    ("Management action", _text(group.get("managementAction"), "Unknown / not supplied")),
                    ("Referenced metrics", f'<ul class="links">{metric_refs}</ul>' if metrics else "No metric references supplied."),
                    ("Child groups", ", ".join(self._group_link(child) for child in _ordered(children)) or "No child groups supplied."),
                ])
                + '<details class="membership"><summary>Member records</summary>'
                + ('<ul class="links">' + "".join(f"<li>{self._item_link(item)}</li>" for item in members) + "</ul>" if members else _empty("No member records supplied."))
                + "</details></article>"
            )
        return '<div class="grid">' + "".join(cards) + "</div>" if cards else _empty("No groups supplied.")

    def highlights(self, entries: list[dict] | None = None) -> str:
        entries = _ordered(self.model.get("highlights", []) if entries is None else entries)
        rows = []
        for entry in entries:
            groups = [self.group_by_id[key] for key in entry.get("groupIds", []) if key in self.group_by_id]
            items = [item for item in self.items if item["id"] in entry.get("itemIds", [])]
            references = [self._group_link(group) for group in _ordered(groups)]
            references.extend(self._item_link(item) for item in items)
            rows.append(
                f'<li>{_badge(entry.get("status"))}<h3>{_text(entry.get("title"))}</h3>'
                f'<p class="muted">{_text(entry.get("type"), "Type not supplied")}</p>'
                f'<p>{_text(entry.get("summary"), "Summary not supplied.")}</p>'
                f'<p class="signal-refs">References: {", ".join(references) or "Not supplied"}</p></li>'
            )
        return '<ul class="signals">' + "".join(rows) + "</ul>" if rows else _empty("No highlights supplied.")

    def trends(self) -> str:
        cards = []
        for trend in _ordered(self.model.get("trends", [])):
            observations = sorted(trend.get("observations", []), key=lambda row: (row["date"], str(row.get("label", "")), row["value"]))
            chart = _empty("No dated observations supplied.")
            if observations:
                values = [float(row["value"]) for row in observations]
                dates = [_date(row.get("date")) for row in observations]
                if all(math.isfinite(value) for value in values) and all(dates):
                    low, high = min(0.0, min(values)), max(0.0, max(values))
                    # Normalize first to avoid overflow for large signed observations.
                    magnitude = max(abs(low), abs(high)) or 1.0
                    low, high = low / magnitude, high / magnitude
                    span = high - low or 1.0
                    days = max(1, (dates[-1] - dates[0]).days)
                    xs = [24 + (452 * (day - dates[0]).days / days) for day in dates]
                    if dates[-1] == dates[0]:
                        xs = [250.0] * len(dates)
                    ys = [136 - (112 * (value / magnitude - low) / span) for value in values]
                    zero = 136 - 112 * (0 - low) / span
                    points = " ".join(f"{x:.3f},{y:.3f}" for x, y in zip(xs, ys))
                    chart = (
                        f'<svg class="chart" viewBox="0 0 500 160" role="img" aria-label="{_text(trend.get("label"))}: dated observations in {_text(trend.get("unit"))}">'
                        f'<title>{_text(trend.get("label"))} — {_text(trend.get("unit"))}</title>'
                        f'<line class="baseline" x1="24" x2="476" y1="{zero:.3f}" y2="{zero:.3f}"/>'
                        f'<polyline class="series" points="{points}"/>'
                        + "".join(
                            f'<circle class="point" cx="{x:.3f}" cy="{y:.3f}" r="4"><title>'
                            f'{_text(row["date"])}: {_text(row["value"])} {_text(trend.get("unit"))}'
                            f'</title></circle>' for x, y, row in zip(xs, ys, observations)
                        ) + "</svg>"
                    )
                else:
                    chart = _empty("Chart unavailable: observations require valid dates and finite values.")
                chart += (
                    '<div class="table-wrap"><table><caption>Dated observations · '
                    f'{_text(trend.get("unit"), "unit not supplied")}</caption><thead><tr>'
                    '<th scope="col">Date</th><th scope="col">Value / unit</th><th scope="col">Label</th>'
                    "</tr></thead><tbody>" + "".join(
                        f'<tr><td>{_text(row.get("date"))}</td><td>{_text(row.get("value"))} '
                        f'{_text(trend.get("unit"))}</td><td>{_text(row.get("label"))}</td></tr>'
                        for row in observations
                    ) + "</tbody></table></div>"
                )
            cards.append(
                f'<article class="card trend-card" data-trend-id="{_text(trend["id"])}">'
                f'<h3>{_text(trend.get("label"))}</h3>{_badge(trend.get("status"))}'
                f'<p class="unit">{_text(trend.get("unit"), "Unit not supplied")} · zero baseline; date-spaced observations</p>{chart}</article>'
            )
        return '<div class="grid">' + "".join(cards) + "</div>" if cards else _empty("No trend history supplied.")

    def section(self, title: str, content: str, copy: str = "") -> str:
        return f'<section><h2>{escape(title)}</h2>' + (f'<p class="section-copy">{escape(copy)}</p>' if copy else "") + content + "</section>"

    def stats(self, entries: list[tuple[str, int, str | None]]) -> str:
        cards = []
        for label, count, destination in entries:
            content = f"<strong>{count}</strong><span>{escape(label)}</span>"
            cards.append(
                f'<a class="stat" href="{escape(destination)}">{content}</a>' if destination
                else f'<div class="stat">{content}</div>'
            )
        return '<div class="stats">' + "".join(cards) + "</div>"

    def status_counts(self, items: list[dict]) -> str:
        counts = Counter(item.get("status") or "unknown" for item in items)
        return self.stats([(f"{status} records", count, None) for status, count in sorted(counts.items())]) if counts else _empty("No record statuses supplied.")

    def _footer(self) -> str:
        provenance = self.model.get("provenance", {})
        adapter = provenance.get("adapter", {})
        sources = provenance.get("sources", [])
        counts = provenance.get("recordCounts", {})
        source_html = "<ul>" + "".join(
            f'<li>{_text(source.get("name"))} · {_text(source.get("type"))} · Retrieved: '
            f'{_text(source.get("retrievedAt"))} · Records: {_text(source.get("recordCount"))}</li>'
            for source in sources
        ) + "</ul>" if sources else "<p>No provenance sources supplied.</p>"
        return (
            '<footer><h2>Provenance &amp; source navigation</h2>'
            + self._links(self.model.get("links"), "No report links supplied.")
            + _fields([
                ("Report ID", _text(self.model.get("report", {}).get("id"))),
                ("Generated at", _text(self.model.get("report", {}).get("generatedAt"))),
                ("Data as of", _text(self.model.get("report", {}).get("dataAsOf"))),
                ("Schema", _text(self.model.get("schemaVersion"))),
                ("Adapter", f'{_text(adapter.get("id"))} · {_text(adapter.get("version"))}'),
                ("Canonical records", str(len(self.items))),
            ])
            + source_html
            + ("<p>Source record counts: " + "; ".join(f"{_text(key)}: {_text(value)}" for key, value in sorted(counts.items())) + "</p>" if counts else "<p>No source record counts supplied.</p>")
            + "</footer>"
        )

    def page(self, filename: str, title: str, content: str, selected: int, nav: list[tuple[str, str]]) -> str:
        report = self.model.get("report", {})
        freshness_class, freshness = _freshness(report, self.config)
        period = report.get("period", {})
        navigation = "".join(
            f'<a href="{escape(destination)}"' + (' aria-current="page"' if filename == destination else "")
            + f">{escape(label)}</a>" for label, destination in nav
        )
        primary = self.config.get("theme", {}).get("primaryColor")
        theme = f"body.{self.template_id}{{--accent:{primary}}}" if isinstance(primary, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", primary) else ""
        preview = (
            '<aside class="notice" aria-label="Preview notice"><strong>Preview report</strong>'
            '<p>Generated from canonical data for review.</p></aside>'
            if self.config.get("output", {}).get("includePrototypeNotice") else ""
        )
        coverage = (
            f"Overview of {len(self.groups)} groups and {len(self.items)} canonical records"
            if self.template_id == "portfolio-team" and filename == "index.html"
            else f"{selected} of {len(self.items)} canonical records"
        )
        return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{escape(_CSP, quote=True)}">
<meta name="description" content="{_text(report.get('subtitle'), title)}">
<title>{escape(title)} | {_text(report.get('title'))} | ReportKit</title><style>{_CSS}{theme}</style></head>
<body class="{self.template_id}" data-template="{self.template_id}" data-template-version="1.0"
 data-item-count="{len(self.items)}" data-selected-item-count="{selected}">
<a class="skip" href="#main">Skip to report</a>
<header><div class="shell mast"><span class="brand">ReportKit · {escape(_TITLES[self.template_id])} v1.0</span>
<span class="classification">Classification: {_text(report.get('classification'), 'Unknown')}</span></div>
<div class="shell hero"><div><p class="eyebrow">{escape(title)}</p><h1>{_text(report.get('title'))}</h1>
<p class="subtitle">{_text(report.get('subtitle'), '')}</p><p class="subtitle">Period: {_text(period.get('label'))}
 · Start: {_text(period.get('startDate'))} · End: {_text(period.get('endDate'))}</p></div>
<section class="report-status" aria-label="Supplied overall report status"><p class="eyebrow">Overall report status</p>
<h2>{_badge(report.get('status'))} {_text(report.get('statusLabel'), '')}</h2>
<p>{_text(report.get('statusSummary'), 'Status rationale not supplied. No status is inferred from metrics.')}</p>
<div class="metadata"><span>Data as of<strong>{_display_instant(report.get('dataAsOf'))}</strong></span>
<span>Generated at<strong>{_display_instant(report.get('generatedAt'))}</strong></span>
<span class="freshness {freshness_class}">Freshness: {escape(freshness)}</span>
<span>View coverage<strong>{coverage}</strong></span></div></section></div></header>
<div class="shell"><nav class="nav" aria-label="Report pages">{navigation}</nav>
<main id="main">{preview}{content}</main>{self._footer()}</div></body></html>"""

    def action(self) -> dict[str, str]:
        generated = _instant(self.model.get("report", {}).get("generatedAt"))
        today = generated.date() if generated else None
        eligible = [item for item in self.items if item.get("status") not in _RESOLVED or _has_blocker(item)]
        selections = [
            ("index.html", "All attention", [item for item in self.items if item.get("status") in _ATTENTION or _has_blocker(item)]),
            ("overdue.html", "Overdue", [item for item in eligible if today and _date(item.get("dueDate")) and _date(item["dueDate"]) < today]),
            ("blocked.html", "Blocked", [item for item in eligible if item.get("status") == "blocked" or _has_blocker(item)]),
            ("due-next-seven-days.html", "Due in the next seven days", [item for item in eligible if today and _date(item.get("dueDate")) and today <= _date(item["dueDate"]) <= today + timedelta(days=7)]),
            ("all-records.html", "All records", self.items),
        ]
        nav = [(label, filename) for filename, label, _ in selections]
        cards = self.stats([(label, len(items), filename) for filename, label, items in selections])
        rule = (
            "Attention includes warning, critical, blocked, failed, in-progress, pending-review and not-started statuses, or an explicit blocker. "
            "Overdue is strictly before the generated UTC date; due next seven days includes that date through seven days later. "
            "Healthy, passed, complete and not-applicable records are excluded from date and blocked queues unless they have an explicit blocker. "
            "Queues may overlap; counts are not additive. Ordering: priority, explicit blocker first, due date, then ID."
        )
        result = {}
        for filename, title, items in selections:
            content = cards + self.section(title, self.records(items, title), f"Snapshot UTC date: {today.isoformat() if today else 'Unknown; date filters unavailable'}. {len(items)} matching records.")
            content += f'<details class="appendix"><summary>Queue definitions</summary><p>{escape(rule)}</p></details>'
            if filename == "index.html":
                content += self.section("Supplied metrics", self.metrics())
                content += self.section("Ownership groups", self.group_cards())
                content += self.section("Supplied signals", self.highlights())
                content += self.section("Dated trend context", self.trends())
            result[filename] = self.page(filename, title, content, len(items), nav)
        return result

    def portfolio(self) -> dict[str, str]:
        nav = [("Portfolio overview", "index.html"), ("All records", "all-records.html")]
        grouped = set().union(*self.members.values()) if self.members else set()
        ungrouped = [item for item in self.items if item["id"] not in grouped]
        content = self.stats([
            ("Supplied groups", len(self.groups), None), ("Distinct canonical records", len(self.items), "all-records.html"),
            ("Ungrouped records", len(ungrouped), "#ungrouped"),
        ])
        content += self.section("Organization summary", self.metrics(), "Supplied measures; group status is source-provided, not calculated from record counts.")
        content += self.section("Team and project rollups", self.group_cards(), "Every group opens a real member report. Membership combines both canonical membership directions and all descendants; shared records are counted once per group.")
        content += self.section("Management focus & supplied signals", self.highlights())
        content += '<section id="ungrouped"><h2>Ungrouped records</h2><p class="section-copy">No membership was supplied in any group or item.</p>' + self.records(ungrouped, "Ungrouped records") + "</section>"
        content += self.section("Portfolio trends", self.trends())
        result = {
            "index.html": self.page("index.html", "Portfolio overview", content, len(ungrouped), nav),
            "all-records.html": self.page("all-records.html", "All portfolio records", self.section("All portfolio records", self.records(self.items, "All portfolio records")), len(self.items), nav),
        }
        for group in self.groups:
            filename = self.group_pages[group["id"]]
            members = [item for item in self.items if item["id"] in self.members[group["id"]]]
            children = [self.group_by_id[key] for key in group.get("childGroupIds", []) if key in self.group_by_id]
            parents = [parent for parent in self.groups if group["id"] in parent.get("childGroupIds", [])]
            metrics = [self.metric_by_id[key] for key in group.get("metricIds", []) if key in self.metric_by_id]
            summary = (
                f'<article class="card" data-group-id="{_text(group["id"])}"><h2>{_text(group.get("label"))}</h2>'
                f'{_badge(group.get("status"))}<p>{_text(group.get("summary"), "Summary not supplied.")}</p>'
                + _fields([
                    ("Group type", _text(group.get("type"))),
                    ("Accountable owner", _owner(group.get("accountableOwner"))),
                    ("Management action", _text(group.get("managementAction"), "Unknown / not supplied")),
                    ("Parent groups", ", ".join(self._group_link(parent) for parent in parents) or "No parent groups supplied."),
                ]) + "</article>"
            )
            body = self.section("Group brief", summary) + self.status_counts(members)
            body += self.section("Referenced metrics", self.metrics(metrics))
            body += self.section("Child group navigation", self.group_cards(_ordered(children)))
            body += self.section("Member action queue", self.records(members, str(group.get("label", "Group")) + " members"), "Union of direct membership and descendants; deduplicated by canonical item ID.")
            signals = [highlight for highlight in self.model.get("highlights", []) if group["id"] in highlight.get("groupIds", []) or set(highlight.get("itemIds", [])) & self.members[group["id"]]]
            body += self.section("Referenced group signals", self.highlights(signals))
            result[filename] = self.page(filename, str(group.get("label", "Group")), body, len(members), nav + [(str(group.get("label", "Group")), filename)])
        return result

    def operational(self) -> dict[str, str]:
        signals = [item for item in self.items if item.get("status") in {"warning", "critical", "blocked", "failed"} or _has_blocker(item)]
        content = self.section("Operational measures", self.metrics(), "All supplied measurements, targets and deltas. Numeric values do not determine service status.")
        content += self.section("Dated signal history", self.trends(), "Actual observation dates and values; zero and negative values are retained. Lines connect observations only, not forecasts.")
        content += '<div class="two-column">'
        content += self.section("Reliability & failure signals", self.status_counts(signals) + (
            '<ul class="signals">' + "".join(
                f'<li>{_badge(item.get("status"))}<h3>{self._item_link(item)}</h3>'
                f'<p>{_text(item.get("statusText"), "Status detail not supplied.")}</p>'
                f'<p>Blocker: {_text(item.get("blocker"))}</p></li>' for item in signals
            ) + "</ul>" if signals else _empty("No warning, critical, blocked or failed records, or explicit blockers, were supplied. This does not establish overall health.")
        ))
        content += self.section("Reported changes & recovery context", self.highlights(), "Solutions and recovery actions are unknown unless supplied as record next actions; no cause is inferred.") + "</div>"
        content += self.section("Service / group health matrix", self.group_cards(), "Source-provided group statuses and metric references; member links open the complete issue record.")
        content += self.section("Complete incident / issue register", self.records(self.items, "All operational records"), "All canonical records are visible, including resolved and unknown statuses. Accountable owner, action owner, due date and ETA remain separate.")
        return {"index.html": self.page("index.html", "Service operations brief", content, len(self.items), [("Operational report", "index.html")])}

    def compliance(self) -> dict[str, str]:
        gates = (
            '<ol class="gate-list">' + "".join(
                f'<li><div><strong>{self._group_link(group)}</strong>'
                f'<span class="muted">{_text(group.get("type"), "Group type not supplied")}</span></div>'
                f'{_badge(group.get("status"))}</li>' for group in self.groups
            ) + "</ol>"
        ) if self.groups else _empty("No domains or gate groups supplied. Readiness is unknown.")
        content = '<div class="notice"><strong>Assessment boundary</strong><p>Requirement and domain labels below organize supplied records; they do not establish a control framework. A group is a release gate only if the source identifies it as such. No release approval, evidence sufficiency or exception approval is inferred.</p></div>'
        content += self.section("Supplied readiness measures", self.metrics())
        content += '<div class="two-column">'
        content += self.section("Domain / gate assessment register", gates, "Only supplied groups and statuses appear here; this is not a fabricated release checklist.")
        content += self.section("Assessment distribution", self.status_counts(self.items), "Counts are canonical records by their supplied status, not invented control totals.") + "</div>"
        content += self.section("Control domains & ownership", self.group_cards(), "Membership includes descendant groups and is deduplicated. Evidence remains attached to its actual requirement record.")
        content += self.section("Requirement & evidence register", self.records(self.items, "Requirement records", compliance=True), "Expand or collapse individual requirements without JavaScript. All details are expanded initially for print.")
        content += self.section("Exceptions & review decisions", '<p class="notice">A separate exceptions collection and exception approval state are not supplied by the canonical model. Any exception records or decisions supplied as items or highlights remain visible with their original status; no exception is assumed approved.</p>' + self.highlights())
        content += self.section("Assessment history", self.trends())
        return {"index.html": self.page("index.html", "Evidence & readiness review", content, len(self.items), [("Readiness report", "index.html")])}


def render_builtin_pages(template_id: str, model: dict, config: dict) -> dict[str, str]:
    """Return complete HTML pages; callers validate canonical input and output."""
    if template_id not in _TITLES:
        raise ValueError(f"Unknown built-in renderer: {template_id}")
    renderer = _Renderer(template_id, model, config)
    return {
        "action-risk": renderer.action,
        "portfolio-team": renderer.portfolio,
        "operational-health": renderer.operational,
        "compliance-readiness": renderer.compliance,
    }[template_id]()
