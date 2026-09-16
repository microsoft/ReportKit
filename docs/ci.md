# CI and screenshot baselines

The Python job runs the complete test suite in a normal Git checkout. The source-tree hygiene
test rejects local environments, Python caches, and packaging artifacts; Git metadata is allowed.
Distribution archives must still exclude `.git` and local development dependencies.

Built-in capability digests and declarative text-file digests normalize CRLF and CR to LF before
hashing. Other byte changes still change the digest. The built-in regression test compares every
generated file across all three line-ending forms.

## Reproducible screenshots

The visual job uses the Playwright 1.63.0 Noble container pinned by image digest in
`.github/workflows/ci.yml`. This fixes the browser, fonts, and operating-system libraries used for
baseline capture. Keep the container version aligned with `tests/visual/package-lock.json`.
CI regenerates both example reports and all 19 screenshots, then requires an exact Git diff match.
The artifact check remains blocking.

`scripts/capture-screenshots.mjs` defaults to the Playwright-managed Chromium browser, without
silently falling back to a different browser. For local Windows design review only, set
`REPORTKIT_SCREENSHOT_CHANNEL=msedge` to explicitly select installed Edge. Windows screenshots
must not replace the Linux CI baselines.

## Updating a baseline

1. Push the intended source change and inspect the visual job's generation and capture logs.
2. Download `reportkit-visual-captures` from that exact run. Artifacts expire after seven days.
3. Review the screenshots, including desktop, full-page, mobile, and interaction states. Do not
   accept changes just because the artifact check failed.
4. Copy only the reviewed PNGs into `docs/assets/screenshots`, preserving their relative paths,
   and commit them with the related change.
5. Require a new CI run to pass both the Python suite and exact artifact comparison.

Generated HTML or manifest differences must be understood and fixed or regenerated separately;
updating screenshot baselines must not hide them. No workflow automatically approves baselines.
