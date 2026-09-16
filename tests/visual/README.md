# Development-only browser checks

These tools capture deterministic local screenshots and run basic accessibility smoke checks. They are not
part of the ReportKit skill runtime, generated reports, or package-distribution model.
Use Node.js 20+ (CI uses Node.js 22) and the pinned development dependencies:

```powershell
npm --prefix tests\visual ci --registry=https://registry.npmjs.org
Push-Location tests\visual
npx playwright install chromium
Pop-Location
node scripts\check-accessibility.mjs
node scripts\capture-screenshots.mjs
```

Build the public examples first with `python -B scripts/build-examples --overwrite`.
The browser install above uses the project's pinned Playwright, not a global installation.
The current authoring environment could not complete a fresh public-registry install because of TLS
handshake failures; see [CI notes](../../docs/ci.md). Do not disable TLS verification.

Screenshot capture:

- Opens local public-sample HTML
- Uses pinned Playwright Chromium by default; Edge requires explicit local-review opt-in
- Applies fixed viewport, light mode, scale factor, and reduced motion
- Fails on missing pages or horizontal overflow
- Writes stable PNG names under `docs\assets\screenshots`
- Never uploads or publishes assets

The accessibility gate opens the five generated built-in example landing pages, checks headings,
the main landmark, link names and image alt attributes, and actually presses Tab to check link
reachability and visible outline focus. It blocks and rejects external resource requests. It does not
check every companion page, contrast, screen-reader behavior, or full WCAG conformance.
Both tools accept `REPORTKIT_VISUAL_NODE_MODULES` for an existing dependency directory.
Accessibility always requires Playwright Chromium; it does not permit the Edge override.

Only the digest-pinned Linux image in CI defines screenshot baselines; local Windows/macOS captures
are previews, not replacements. That image already contains the matching Chromium browser.
Remove `tests\visual\node_modules` before preparing a public archive. It is ignored and must not be
included in repository ZIPs.

## Archived narrated video (optional Windows authoring only)

The existing narrated video and its script are archived historical material, **not fresh evidence
of current renderer capabilities**. The narration describes an older single-renderer state and must
be revised and reviewed before producing a current promotional video. CI neither produces nor
validates it.

FFmpeg is not needed for browser checks and `ffmpeg-static` is no longer installed by default.
Only if explicitly producing that archived video locally, the existing producer expects the optional
`ffmpeg-static` package alongside Playwright. Install these separately (this opt-in package downloads
an FFmpeg binary), not into the visual CI dependency manifest:

```powershell
npm install --prefix .reportkit-video-deps --no-save --package-lock=false --registry=https://registry.npmjs.org playwright@1.63.0 ffmpeg-static@5.2.0
$env:REPORTKIT_VISUAL_NODE_MODULES = Join-Path $PWD '.reportkit-video-deps\node_modules'
node scripts\produce-narrated-video.mjs .\ReportKit-video
Remove-Item Env:REPORTKIT_VISUAL_NODE_MODULES
```

Supply a new output directory. This creates a 1920x1080, 30 fps, 60-second MP4 with local
Microsoft Zira synthetic narration, selectable English captions, a sidecar SRT, six scene images,
and a production manifest. Caption timings are sentence-level approximations. Requires Windows
SAPI, installed Microsoft Edge, and the optional Playwright/FFmpeg dependencies above.
No speech service, upload, publication, or existing-output replacement is performed.
Do not include the optional dependency directory or local video output in a public archive.
