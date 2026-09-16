# CI and screenshot baselines

The standard-library Python suite targets Python 3.10+ on Ubuntu, Windows, and macOS.
CI runs Python 3.10 and 3.12 on each OS in normal Git checkouts; matrix jobs do not install browser
or FFmpeg dependencies. The source-tree hygiene
test rejects local environments, Python caches, and packaging artifacts; Git metadata is allowed.
Distribution archives must still exclude `.git` and local development dependencies.

Built-in capability digests and declarative text-file digests normalize CRLF and CR to LF before
hashing. Other byte changes still change the digest. The built-in regression test compares every
generated file across all three line-ending forms.

## Reproducible screenshots

The visual job uses the Playwright 1.63.0 Noble container pinned by image digest in
`.github/workflows/ci.yml`. This fixes the browser, fonts, and operating-system libraries used for
baseline capture. Keep the container version aligned with `tests/visual/package-lock.json`.
The single Linux visual job regenerates all five built-in example sites, the custom example, and
the screenshots listed in the screenshot contract, then requires clean generated artifact scopes.
The artifact check remains blocking.

`python -B scripts/check-generated-clean.py` runs
`git status --porcelain --untracked-files=all --` with these exact path scopes:
`templates`, `showcase`, `examples/operational-snapshot/generated`,
`examples/custom-template-project/generated`, and `docs/assets/screenshots`.
Any staged, unstaged, deleted, renamed, or untracked output in those scopes fails the gate.
Unrelated dirty paths are allowed; the checker never stages files. Git-ignored files remain ignored.
Its isolated-repository tests cover clean output, tracked and untracked drift, and unrelated dirt.
New intended generated files must be reviewed and committed with the change before CI can pass.

`scripts/capture-screenshots.mjs` defaults to the Playwright-managed Chromium browser, without
silently falling back to a different browser. For local Windows design review only, set
`REPORTKIT_SCREENSHOT_CHANNEL=msedge` to explicitly select installed Edge. Windows screenshots
must not replace the Linux CI baselines.

## Local-only review

No push is needed to generate and inspect reports. Run `python -B scripts/build-examples --overwrite`
to refresh the five public examples. The flag permits replacement of ReportKit-owned outputs only.
For matching screenshots, run `scripts/capture-screenshots.mjs` inside the exact container image
declared in CI, with the repository mounted as the working directory and Playwright dependencies
available through `REPORTKIT_VISUAL_NODE_MODULES`. The container can run with `--network none`
once the image and development dependencies are present.

For native local setup, install the locked dependencies with
`npm --prefix tests/visual ci --registry=https://registry.npmjs.org`, then run
`npx playwright install chromium` **from `tests/visual`** to install the matching browser.
See [browser setup](../tests/visual/README.md) for PowerShell commands.
The pinned Linux container already includes this browser.

## Basic browser accessibility gate

`node scripts/check-accessibility.mjs` uses the same pinned Playwright dependency and Chromium
installation as screenshot capture. It loads the five real generated built-in `index.html` pages;
it does not substitute marketing prototypes. It checks a single visible h1 and main landmark,
nonempty ordered headings without skipped levels, browser-computed nonempty link names, and explicit
image alt attributes (empty alt is permitted for decorative images). It presses Tab from initial
document focus to require every visible link to be reachable, brought into view, and visibly focused
with a nontransparent outline of at least two CSS pixels. External resource requests are blocked
and fail the check. No dependency beyond existing Playwright is added.

For an offline container with dependencies mounted at `/deps/node_modules`, run:

```sh
REPORTKIT_VISUAL_NODE_MODULES=/deps/node_modules node scripts/check-accessibility.mjs
```

This is a smoke gate, **not WCAG certification**. It does not inspect every companion page,
validate the quality of alt text, assess screen-reader announcements, test link activation, or measure
color contrast. Gradient/translucent backgrounds require a separate visual/contrast assessment;
computed foreground color alone would not establish a reliable ratio. Visible-focus checks require
the current outline design rather than accepting arbitrary box-shadow-only focus styling.

Every GitHub Action is pinned to an immutable commit SHA. Update a pin only after verifying its
upstream version and reviewing the change.

The visual lockfile uses public `registry.npmjs.org` tarball URLs. The current lock was regenerated
offline from the existing dependency graph and integrity hashes after the public registry returned
a TLS handshake failure in this authoring environment. Versions and integrity values were preserved;
a clean online `npm ci` against the public registry still needs verification where access works.
No TLS checks were disabled.
The unused `ffmpeg-static` downloader and its transitive graph were removed with an offline,
package-lock-only npm update. Playwright versions and existing integrity hashes were preserved,
including SHA-1 values inherited from the available graph; SHA-512 values were not invented.
No matching public-registry tarball was available in the local npm cache to independently strengthen
those hashes. CI uses no FFmpeg downloader. The old narrated video is archived historical material,
not proof of the current generated examples; optional local production setup is documented separately.

## Updating a baseline

1. Push the intended source change and inspect the visual job's generation and capture logs.
2. Download `reportkit-visual-captures` from that exact run. Artifacts expire after seven days.
3. Review the screenshots, including desktop, full-page, mobile, and interaction states. Do not
   accept changes just because the artifact check failed.
4. Copy only the reviewed PNGs into `docs/assets/screenshots`, preserving their relative paths,
   and commit them with the related change.
5. Require a new CI run to pass the Python matrix, browser accessibility gate, and clean-output check.

Generated HTML or manifest differences must be understood and fixed or regenerated separately;
updating screenshot baselines must not hide them. No workflow automatically approves baselines.
