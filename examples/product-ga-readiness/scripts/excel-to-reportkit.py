"""Convert the governed Product GA Readiness workbook to ReportKit JSON."""

from __future__ import annotations

import argparse
import json
import posixpath
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile

MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"m": MAIN_NS, "r": REL_NS, "p": PACKAGE_REL_NS}
CELL_ID = re.compile(r"^([A-Z]+)([1-9]\d*)$")
VALID_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")

STATUS_MAP = {
    "Complete": "complete",
    "Ready": "healthy",
    "On Track": "healthy",
    "At Risk": "critical",
    "Blocked": "blocked",
    "Update Required": "warning",
    "Pending Review": "pending-review",
    "In Progress": "in-progress",
    "Not Started": "not-started",
    "Unknown": "unknown",
    "N/A": "not-applicable",
}
EVIDENCE_MAP = {
    "Not Required": "not-required",
    "Missing": "missing",
    "Partial": "partial",
    "Submitted": "submitted",
    "Verified": "verified",
    "Rejected": "rejected",
    "Unknown": "unknown",
}
STATUS_WEIGHT = {
    "unknown": 0,
    "not-applicable": 0,
    "complete": 1,
    "passed": 1,
    "healthy": 1,
    "in-progress": 2,
    "pending-review": 3,
    "not-started": 3,
    "warning": 4,
    "critical": 5,
    "blocked": 6,
    "failed": 6,
}


def _archive_path(base: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    return posixpath.normpath(str(PurePosixPath(base).parent.joinpath(target)))


def _column_number(reference: str) -> int:
    match = CELL_ID.fullmatch(reference)
    if not match:
        raise ValueError(f"Invalid cell reference '{reference}'.")
    value = 0
    for character in match.group(1):
        value = value * 26 + ord(character) - ord("A") + 1
    return value


def _range_bounds(reference: str) -> tuple[int, int, int, int]:
    start, end = reference.split(":")
    start_match = CELL_ID.fullmatch(start)
    end_match = CELL_ID.fullmatch(end)
    if not start_match or not end_match:
        raise ValueError(f"Invalid table range '{reference}'.")
    return (
        _column_number(start),
        int(start_match.group(2)),
        _column_number(end),
        int(end_match.group(2)),
    )


class Workbook:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.archive = ZipFile(path)
        self.shared_strings = self._read_shared_strings()
        self.sheets = self._read_sheets()

    def close(self) -> None:
        self.archive.close()

    def _read_shared_strings(self) -> list[str]:
        try:
            root = ET.fromstring(self.archive.read("xl/sharedStrings.xml"))
        except KeyError:
            return []
        return ["".join(node.text or "" for node in item.iter(f"{{{MAIN_NS}}}t")) for item in root]

    def _read_sheets(self) -> dict[str, str]:
        workbook = ET.fromstring(self.archive.read("xl/workbook.xml"))
        relationships = ET.fromstring(self.archive.read("xl/_rels/workbook.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        result: dict[str, str] = {}
        sheets = workbook.find("m:sheets", NS)
        if sheets is None:
            raise ValueError("Workbook has no sheets.")
        for sheet in sheets:
            relationship_id = sheet.attrib[f"{{{REL_NS}}}id"]
            result[sheet.attrib["name"]] = _archive_path("xl/workbook.xml", targets[relationship_id])
        return result

    def _cell_value(self, cell: ET.Element) -> Any:
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            return "".join(node.text or "" for node in cell.iter(f"{{{MAIN_NS}}}t"))
        value_node = cell.find("m:v", NS)
        if value_node is None or value_node.text is None:
            return ""
        value = value_node.text
        if cell_type == "s":
            return self.shared_strings[int(value)]
        if cell_type in {"str", "e"}:
            return value
        if cell_type == "b":
            return value == "1"
        try:
            return float(value) if "." in value or "e" in value.lower() else int(value)
        except ValueError:
            return value

    def read_table(self, sheet_name: str, table_name: str) -> list[dict[str, Any]]:
        sheet_path = self.sheets.get(sheet_name)
        if not sheet_path:
            raise ValueError(f"Workbook is missing sheet '{sheet_name}'.")
        rels_path = str(PurePosixPath(sheet_path).parent / "_rels" / f"{PurePosixPath(sheet_path).name}.rels")
        relationships = ET.fromstring(self.archive.read(rels_path))
        relationship_targets = {item.attrib["Id"]: item.attrib["Target"] for item in relationships}
        sheet = ET.fromstring(self.archive.read(sheet_path))
        table_path = None
        for table_part in sheet.findall(".//m:tablePart", NS):
            relationship_id = table_part.attrib[f"{{{REL_NS}}}id"]
            candidate = _archive_path(sheet_path, relationship_targets[relationship_id])
            table = ET.fromstring(self.archive.read(candidate))
            if table.attrib.get("name") == table_name or table.attrib.get("displayName") == table_name:
                table_path = candidate
                break
        if not table_path:
            raise ValueError(f"Sheet '{sheet_name}' is missing table '{table_name}'.")

        table = ET.fromstring(self.archive.read(table_path))
        headers = [column.attrib["name"] for column in table.findall("m:tableColumns/m:tableColumn", NS)]
        start_column, start_row, end_column, end_row = _range_bounds(table.attrib["ref"])
        if end_column - start_column + 1 != len(headers):
            raise ValueError(f"Table '{table_name}' column metadata does not match its range.")
        cells = {
            cell.attrib["r"]: self._cell_value(cell)
            for cell in sheet.findall(".//m:sheetData/m:row/m:c", NS)
        }
        rows: list[dict[str, Any]] = []
        for row_number in range(start_row + 1, end_row + 1):
            values: list[Any] = []
            for column_number in range(start_column, end_column + 1):
                column = ""
                value = column_number
                while value:
                    value, remainder = divmod(value - 1, 26)
                    column = chr(ord("A") + remainder) + column
                values.append(cells.get(f"{column}{row_number}", ""))
            if any(value != "" and value is not None for value in values):
                rows.append(dict(zip(headers, values)))
        return rows


def normalize_status(value: Any) -> str:
    text = str(value)
    if text not in STATUS_MAP:
        raise ValueError(f"Unsupported status '{text}'. Use an allowed value from the Instructions sheet.")
    return STATUS_MAP[text]


def normalize_priority(value: Any) -> str:
    text = str(value or "unknown").lower()
    return text if text in {"critical", "high", "medium", "low", "unknown"} else "unknown"


def excel_datetime(value: float) -> datetime:
    return datetime(1899, 12, 30, tzinfo=timezone.utc) + timedelta(days=value)


def date_only(value: Any, field: str) -> str | None:
    if value in ("", None):
        return None
    if isinstance(value, (int, float)):
        return excel_datetime(float(value)).date().isoformat()
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError as exception:
        raise ValueError(f"{field} has invalid date '{text}'.") from exception


def date_time(value: Any, field: str) -> str:
    if isinstance(value, (int, float)):
        return excel_datetime(float(value)).isoformat().replace("+00:00", "Z")
    text = str(value).strip()
    if text.endswith(" UTC"):
        text = f"{text[:-4]}+00:00"
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exception:
        raise ValueError(f"{field} has invalid date-time '{text}'.") from exception
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def owner(value: Any) -> dict[str, str] | None:
    text = str(value or "").strip()
    return {"displayName": text} if text else None


def integer(value: Any, fallback: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def require_unique_ids(rows: list[dict[str, Any]], column: str, label: str) -> None:
    seen: set[str] = set()
    for row in rows:
        identifier = str(row.get(column) or "").strip()
        if not VALID_ID.fullmatch(identifier):
            raise ValueError(f"{label} has an invalid {column}: '{identifier}'.")
        if identifier in seen:
            raise ValueError(f"{label} contains duplicate {column} '{identifier}'.")
        seen.add(identifier)


def yes_no(value: Any, field: str) -> bool:
    text = str(value)
    if text not in {"Yes", "No"}:
        raise ValueError(f"{field} must be Yes or No.")
    return text == "Yes"


def progress_percent(value: Any, field: str) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError) as exception:
        raise ValueError(f"{field} must be between 0% and 100%.") from exception
    if not 0 <= number <= 1:
        raise ValueError(f"{field} must be between 0% and 100%.")
    return round(number * 100)


def convert(input_path: Path, output_directory: Path) -> None:
    workbook = Workbook(input_path)
    try:
        settings_rows = workbook.read_table("Report Setup", "ReportSettingsTable")
        gates = workbook.read_table("Readiness Gates", "ReadinessGatesTable")
        milestones = workbook.read_table("Milestones", "MilestonesTable")
        decisions = workbook.read_table("Decisions & Support", "DecisionsSupportTable")
        audiences = workbook.read_table("Audience Adoption", "AudienceAdoptionTable")
        records = workbook.read_table("Readiness Details", "ReadinessDetailsTable")
    finally:
        workbook.close()

    settings = {str(row["Key"]): row["Value"] for row in settings_rows}
    required_settings = [
        "Report ID", "Report Title", "Subtitle", "Product Name", "Primary GA Target",
        "GA Target Label", "GA Target Date", "Data As Of", "Generated At", "Classification",
        "Overall Status", "Overall Status Label", "Overall Status Summary", "Decision Question",
        "Refresh Cadence", "Report Period Start", "Report Period End", "Template ID", "Template Version",
    ]
    missing = [key for key in required_settings if str(settings.get(key, "")).strip() == ""]
    if missing:
        raise ValueError(f"Missing required Report Setup values: {', '.join(missing)}")

    require_unique_ids(gates, "Gate ID", "Readiness Gates")
    require_unique_ids(records, "Record ID", "Readiness Details")
    require_unique_ids(milestones, "Milestone ID", "Milestones")
    require_unique_ids(decisions, "Request ID", "Decisions & Support")
    require_unique_ids(audiences, "Audience ID", "Audience Adoption")

    for row in gates:
        normalize_status(row["Status"])
        yes_no(row["Blocks GA"], f"Gate {row['Gate ID']} Blocks GA")
        date_only(row.get("Target Date"), f"Gate {row['Gate ID']} Target Date")
    for row in records:
        normalize_status(row["Status"])
        if not str(row.get("Owner") or "").strip():
            raise ValueError(f"Record {row['Record ID']} must name an Owner or use 'Unassigned'.")
        if not str(row.get("Workstream ID") or "").strip():
            raise ValueError(f"Record {row['Record ID']} is missing Workstream ID.")
        yes_no(row["Blocks GA"], f"Record {row['Record ID']} Blocks GA")
        date_only(row.get("Target Date"), f"Record {row['Record ID']} Target Date")
    for row in milestones:
        normalize_status(row["Status"])
        if not str(row.get("Owner") or "").strip():
            raise ValueError(f"Milestone {row['Milestone ID']} must name an Owner or use 'Unassigned'.")
        progress_percent(row["Progress %"], f"Milestone {row['Milestone ID']} Progress %")
        date_only(row.get("Target Date"), f"Milestone {row['Milestone ID']} Target Date")
        date_only(row.get("Completed Date"), f"Milestone {row['Milestone ID']} Completed Date")
    for row in decisions:
        normalize_status(row["Status"])
        if not str(row.get("Owner") or "").strip():
            raise ValueError(f"Request {row['Request ID']} must name an Owner or use 'Unassigned'.")
        yes_no(row["Blocks GA"], f"Request {row['Request ID']} Blocks GA")
        date_only(row.get("Due Date"), f"Request {row['Request ID']} Due Date")
    for row in audiences:
        normalize_status(row["Status"])
        if not str(row.get("Owner") or "").strip():
            raise ValueError(f"Audience {row['Audience ID']} must name an Owner or use 'Unassigned'.")
        yes_no(row["Blocks GA"], f"Audience {row['Audience ID']} Blocks GA")
        progress_percent(row["Progress %"], f"Audience {row['Audience ID']} Progress %")
        date_only(row.get("Target Date"), f"Audience {row['Audience ID']} Target Date")

    decision_records = [{
        "Record ID": row["Request ID"],
        "Workstream ID": "decisions-support",
        "Workstream": "Decisions & support",
        "Item": row["Decision or Support Needed"],
        "Status": row["Status"],
        "Priority": "Critical" if yes_no(row["Blocks GA"], f"Request {row['Request ID']} Blocks GA") else (
            "High" if str(row["Status"]) in {"Blocked", "At Risk"} else "Medium"
        ),
        "Owner": row["Owner"],
        "Accountable Owner": row["Needed From"],
        "Target Date": row["Due Date"],
        "Blocks GA": row["Blocks GA"],
        "GA Impact": row["Outcome Needed"],
        "Current State or Evidence": row["Current Context"],
        "Next Action": row["Next Step"],
        "Evidence State": "Partial",
        "Release Scope": row["Scope or Related Record"],
        "Display Order": row["Display Order"],
        "_category": "decision" if str(row["Type"]).lower() == "decision" else "action",
        "_authoritativeBlocker": False,
    } for row in decisions]
    audience_records = [{
        "Record ID": row["Audience ID"],
        "Workstream ID": "audience-adoption",
        "Workstream": "Target audiences & client adoption",
        "Item": row["Audience or Client"],
        "Status": row["Status"],
        "Priority": "Critical" if yes_no(row["Blocks GA"], f"Audience {row['Audience ID']} Blocks GA") else "Medium",
        "Owner": row["Owner"],
        "Accountable Owner": row["Owner"],
        "Target Date": row["Target Date"],
        "Blocks GA": row["Blocks GA"],
        "GA Impact": (
            f"{row['Type']} · {row['Adoption Stage']} · "
            f"{progress_percent(row['Progress %'], 'Audience ' + str(row['Audience ID']) + ' Progress %')}%"
        ),
        "Current State or Evidence": row["Current Evidence"],
        "Next Action": row["Next Action"],
        "Evidence State": "Verified" if str(row["Status"]) == "Complete" else "Partial",
        "Release Scope": row["Type"],
        "Display Order": row["Display Order"],
        "_category": "deployment",
    } for row in audiences]
    all_records = [*records, *decision_records, *audience_records]
    require_unique_ids(all_records, "Record ID", "Combined tracking data")

    items = []
    for index, row in enumerate(all_records, 1):
        item = {
            "id": str(row["Record ID"]),
            "title": str(row["Item"]),
            "summary": str(row.get("Current State or Evidence") or ""),
            "status": normalize_status(row["Status"]),
            "statusText": str(row.get("Status") or "Unknown"),
            "priority": normalize_priority(row.get("Priority")),
            "category": row.get("_category") or ("requirement" if "launch" in str(row["Workstream ID"]) else "build"),
            "evidenceState": EVIDENCE_MAP.get(str(row.get("Evidence State")), "unknown"),
            "impact": str(row.get("GA Impact") or "No blocker"),
            "groupIds": [str(row["Workstream ID"])],
            "nextAction": str(row.get("Next Action") or "Review required"),
            "order": integer(row.get("Display Order"), index),
        }
        if owner(row.get("Owner")):
            item["actionOwner"] = owner(row["Owner"])
        if owner(row.get("Accountable Owner")):
            item["accountableOwner"] = owner(row["Accountable Owner"])
        due_date = date_only(row.get("Target Date"), f"Record {row['Record ID']} Target Date")
        if due_date:
            item["dueDate"] = due_date
        if (
            row.get("_authoritativeBlocker", True)
            and yes_no(row["Blocks GA"], f"Record {row['Record ID']} Blocks GA")
        ):
            item["blocker"] = "Confirmed GA blocker"
        items.append(item)

    group_rows: dict[str, dict[str, Any]] = {}
    for index, (row, item) in enumerate(zip(all_records, items), 1):
        group_id = str(row["Workstream ID"])
        group_rows.setdefault(group_id, {
            "id": group_id,
            "label": str(row["Workstream"]),
            "rows": [],
            "order": index,
        })["rows"].append((row, item))
    groups = []
    for group in group_rows.values():
        worst = max((item["status"] for _, item in group["rows"]), key=lambda status: STATUS_WEIGHT.get(status, 0))
        open_items = [item for _, item in group["rows"] if item["status"] not in {"complete", "passed", "healthy"}]
        result = {
            "id": group["id"],
            "label": group["label"],
            "type": group["id"],
            "status": worst,
            "summary": (
                f"{len(open_items)} item{'s' if len(open_items) != 1 else ''} require attention."
                if open_items else "All tracked items are ready or complete."
            ),
            "itemIds": [item["id"] for _, item in group["rows"]],
            "managementAction": open_items[0]["nextAction"] if open_items else "Maintain readiness through the GA decision.",
            "order": group["order"],
        }
        accountable = owner(group["rows"][0][0].get("Accountable Owner"))
        if accountable:
            result["accountableOwner"] = accountable
        groups.append(result)

    metrics = [{
        "id": str(row["Gate ID"]),
        "label": str(row["Gate Name"]),
        "value": row["Value"] if isinstance(row["Value"], (int, float)) else str(row.get("Value") or "Not confirmed"),
        "unit": str(row.get("Unit") or "state"),
        "status": normalize_status(row["Status"]),
        "statusLabel": str(row.get("Status Label") or row.get("Status") or "Unknown"),
        "description": str(row.get("Summary") or ""),
        "order": integer(row.get("Display Order"), index),
    } for index, row in enumerate(gates, 1)]
    target_date = datetime.fromisoformat(date_only(settings["GA Target Date"], "GA Target Date"))
    data_as_of = datetime.fromisoformat(date_only(settings["Data As Of"], "Data As Of"))
    days_to_target = max(0, (target_date - data_as_of).days)
    metrics.append({
        "id": "days-to-target",
        "label": "Days to target",
        "value": days_to_target,
        "unit": "days to GA",
        "status": "healthy" if days_to_target > 0 else "critical",
        "statusLabel": "COUNTDOWN" if days_to_target > 0 else "DUE",
        "description": str(settings["GA Target Label"]),
        "order": 999,
    })

    milestone_models = []
    for row in milestones:
        milestone = {
            "id": str(row["Milestone ID"]),
            "label": str(row["Milestone"]),
            "status": normalize_status(row["Status"]),
            "statusText": str(row["Status"]),
            "progressPercent": progress_percent(row["Progress %"], f"Milestone {row['Milestone ID']} Progress %"),
            "summary": str(row.get("Current Evidence") or ""),
            "milestoneType": str(row.get("Milestone Type") or "Milestone"),
            "impact": str(row.get("GA Impact") or ""),
            "dependency": str(row.get("Dependency") or ""),
            "nextAction": str(row.get("Next Action") or ""),
            "order": integer(row.get("Display Order"), 999),
        }
        if owner(row.get("Owner")):
            milestone["owner"] = owner(row["Owner"])
        target = date_only(row.get("Target Date"), f"Milestone {row['Milestone ID']} Target Date")
        completed = date_only(row.get("Completed Date"), f"Milestone {row['Milestone ID']} Completed Date")
        if target:
            milestone["targetDate"] = target
        if completed:
            milestone["completedDate"] = completed
        milestone_models.append(milestone)

    generated_at = date_time(settings["Generated At"], "Generated At")
    canonical = {
        "schemaVersion": "1.0",
        "report": {
            "id": str(settings["Report ID"]),
            "title": str(settings["Report Title"]),
            "subtitle": str(settings["Subtitle"]),
            "generatedAt": generated_at,
            "dataAsOf": date_time(settings["Data As Of"], "Data As Of"),
            "classification": str(settings["Classification"]),
            "status": normalize_status(settings["Overall Status"]),
            "statusLabel": str(settings["Overall Status Label"]),
            "statusSummary": str(settings["Overall Status Summary"]),
            "period": {
                "label": f"{settings['GA Target Label']} GA decision",
                "startDate": date_only(settings["Report Period Start"], "Report Period Start"),
                "endDate": date_only(settings["Report Period End"], "Report Period End"),
            },
            "outlookMilestones": milestone_models,
        },
        "metrics": metrics,
        "groups": groups,
        "items": items,
        "trends": [{
            "id": "confirmed-ga-blockers",
            "label": "Confirmed GA blockers",
            "unit": "blockers",
            "status": "critical" if any(item.get("blocker") == "Confirmed GA blocker" for item in items) else "healthy",
            "observations": [{
                "date": date_only(settings["Data As Of"], "Data As Of"),
                "value": sum(item.get("blocker") == "Confirmed GA blocker" for item in items),
                "label": "Current daily snapshot",
            }],
            "order": 1,
        }],
        "highlights": [{
            "id": f"blocker-{index}",
            "title": item["title"],
            "summary": item["summary"],
            "type": "risk",
            "status": item["status"],
            "itemIds": [item["id"]],
            "groupIds": item["groupIds"],
            "order": index,
        } for index, item in enumerate((item for item in items if item.get("blocker")), 1)],
        "links": [],
        "provenance": {
            "adapter": {"id": "product-ga-readiness-excel", "version": "1.0.0"},
            "sources": [{
                "name": input_path.name,
                "type": "xlsx",
                "retrievedAt": generated_at,
                "recordCount": len(all_records) + len(milestones),
            }],
            "recordCounts": {
                "raw": len(all_records) + len(milestones),
                "gates": len(gates),
                "groups": len(groups),
                "milestones": len(milestones),
                "decisions": len(decisions),
                "audiences": len(audiences),
            },
        },
    }
    configuration = {
        "version": "1.0",
        "template": {"id": str(settings["Template ID"]), "version": str(settings["Template Version"])},
        "theme": {
            "name": "Product GA Readiness",
            "primaryColor": str(settings.get("Primary Color") or "#1557B0"),
        },
        "freshnessThresholdsMinutes": {"fresh": 1440, "stale": 2880},
        "output": {"selfContained": True, "includePrototypeNotice": False},
    }
    output_directory.mkdir(parents=True, exist_ok=True)
    (output_directory / "canonical-report.json").write_text(
        json.dumps(canonical, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_directory / "product-ga-readiness.config.json").write_text(
        json.dumps(configuration, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Converted {len(all_records)} tracking rows, {len(milestones)} milestones, "
        f"and {len(gates)} gates from {input_path.name}."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    arguments = parser.parse_args()
    convert(arguments.input.resolve(), arguments.out_dir.resolve())


if __name__ == "__main__":
    main()
