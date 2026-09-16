# Validation

ReportKit validates both canonical input and generated output.

## Severity

| Severity | Meaning | Publication |
|---|---|---|
| Error | Invalid, unsafe, incomplete, or inconsistent | Blocked |
| Warning | Usable report requiring attention | Allowed |
| Info | Recommendation or optional condition | Allowed |

Publication behavior is the target contract. The publisher is not implemented; current commands
validate and return local artifacts.

## Model validation

Checks include:

- Supported schema and template versions
- Required report metadata
- Valid timestamps and dates
- Unique IDs and resolved references
- Rejection of canonical group cycles
- Explicit metric units
- Ownership, due-date, ETA, status, and next-action semantics
- Provenance
- Prohibited sensitive fields

All five built-in capabilities require `report`. Missing or empty optional collections are valid
and render honest empty states; they must not be silently filled with healthy or invented data.

## Site validation

Checks include:

- Expected files and valid internal links
- Counts matching linked destination pages
- Escaped untrusted data
- Visible freshness and classification
- Script-free core content
- Accessibility structure
- Manifest consistency
- No external `href` or `src` destinations in current self-contained output, including HTTPS anchors

Built-in source/evidence HTTP(S) URLs can appear as escaped text references, not clickable
external links. Generated local report navigation remains clickable.

Validation produces `validation-report.json`. Any error prevents publication.
