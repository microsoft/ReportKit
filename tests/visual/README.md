# Development-only visual capture

This workflow captures deterministic local screenshots for marketing and visual review. It is not
part of the ReportKit skill runtime, generated reports, or package-distribution model.

```powershell
npm --prefix tests\visual install
node scripts\capture-screenshots.mjs
```

The script:

- Opens local public-sample HTML only
- Uses Chromium or the installed Microsoft Edge Chromium channel
- Applies fixed viewport, light mode, scale factor, and reduced motion
- Fails on missing pages or horizontal overflow
- Writes stable PNG names under `docs\assets\screenshots`
- Never uploads or publishes assets

Remove `tests\visual\node_modules` before preparing a public archive. It is ignored and must not be
included in repository ZIPs.

