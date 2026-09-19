# Product GA Readiness example

This project pairs a governed Excel source contract with the reusable
`microsoft/product-ga-readiness` declarative template. The workbook contains all product-specific
identity and readiness facts; the adapter performs deterministic mapping; the template controls
presentation.

## Deliverables

- `Product-GA-Readiness-Input.xlsx` — formatted source workbook populated with a synthetic Contoso example.
- `templates/microsoft-product-ga-readiness/` — declarative ReportKit template pack.
- `scripts/excel-to-reportkit.py` — dependency-free Excel-to-canonical adapter.
- `generated-site/index.html` — static HTML generated from the workbook.
- `AGENCY-IMPLEMENTATION-GUIDE.md` — build and ownership guidance.
- `EXCEL-DATA-CONTRACT.md` — workbook contract.
- `DESIGN-ACCEPTANCE.md` — visual and behavioral acceptance criteria.
- `REPORTKIT-INTEGRATION-NOTES.md` — trusted engine integration notes.

## Source-to-report flow

1. A program owner updates `Report Setup`, `Readiness Gates`, `Milestones`, `Decisions & Support`, `Audience Adoption`, and `Readiness Details` once per business day.
2. The adapter validates the required setup keys and transforms the Excel tables into canonical ReportKit JSON and configuration JSON.
3. ReportKit validates the template pack, canonical model, lock digest, output, and manifest.
4. ReportKit emits a static, script-free, single-page report.

The current workbook intentionally shows two confirmed GA blockers, two unassigned launch owners, and the distinction between an on-track SDK path and an at-risk overall GA decision.

## Build

Run from the repository root:

```powershell
python examples\product-ga-readiness\scripts\excel-to-reportkit.py `
  --input examples\product-ga-readiness\Product-GA-Readiness-Input.xlsx `
  --out-dir examples\product-ga-readiness

python scripts\validate-template `
  examples\product-ga-readiness\templates\microsoft-product-ga-readiness

python scripts\build-template `
  --template examples\product-ga-readiness\templates\microsoft-product-ga-readiness `
  --data examples\product-ga-readiness\canonical-report.json `
  --config examples\product-ga-readiness\product-ga-readiness.config.json `
  --lock examples\product-ga-readiness\reportkit.lock.json `
  --output examples\product-ga-readiness\generated-site `
  --overwrite

python scripts\validate examples\product-ga-readiness\generated-site --kind site
```

The adapter reads only the six named workbook tables documented in
`EXCEL-DATA-CONTRACT.md`. Update the workbook rather than editing generated canonical JSON or HTML.

## Publish through OneDrive synchronization

The existing daily S360 publisher establishes the supported local pattern: build and validate
under the signed-in Windows identity, copy into a synchronized SharePoint folder, and let OneDrive
perform the cloud upload. The workbook in the synchronized `Excel-Data` folder is authoritative.
The publisher reads that workbook, stages the generated HTML, verifies SHA-256 hashes, and
atomically replaces `index.html`.

After using **Add shortcut to OneDrive** for the approved `tokenbinding` and `Excel-Data`
SharePoint folders:

```powershell
pwsh examples\product-ga-readiness\scripts\Publish-Product-GA-Readiness.ps1 `
  -WorkbookPath "$HOME\Microsoft\tbstatus - Documents\Excel-Data\Product-GA-Readiness-Input.xlsx" `
  -HtmlPublishDirectory "$HOME\Microsoft\tbstatus - Documents\tokenbinding"
```

Omit `HtmlPublishDirectory` to rebuild and validate locally without copying the generated page.
