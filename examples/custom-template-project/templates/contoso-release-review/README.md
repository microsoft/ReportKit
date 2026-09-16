# Release Review

A declarative ReportKit template for release owners and approvers deciding whether a release can proceed.

The pack composes only registered ReportKit components. It contains no executable renderer code, HTML, CSS, JavaScript, remote resources, or publication behavior.

Required canonical data:

- Report identity, status, classification, `dataAsOf`, and `generatedAt`
- Metrics with explicit units
- Program groups
- Actionable release decisions

Validate locally:

```powershell
python scripts\validate-template examples\custom-template-project\templates\contoso-release-review
```
