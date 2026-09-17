import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const modules = process.env.REPORTKIT_VISUAL_NODE_MODULES ??
  path.join(root, "tests", "visual", "node_modules");
const { chromium } = await import(pathToFileURL(path.join(modules, "playwright", "index.mjs")).href);
const expected = JSON.parse(await fs.readFile(path.join(root, "tests", "visual", "package.json"), "utf8"));
const installed = JSON.parse(await fs.readFile(path.join(modules, "playwright", "package.json"), "utf8"));
if (installed.version !== expected.devDependencies.playwright) {
  throw new Error(`Expected Playwright ${expected.devDependencies.playwright}; found ${installed.version}`);
}
if (process.env.REPORTKIT_SCREENSHOT_CHANNEL &&
    process.env.REPORTKIT_SCREENSHOT_CHANNEL !== "chromium") {
  throw new Error("The accessibility gate requires pinned Playwright Chromium, not a local browser channel.");
}
const examples = [
  "executive-health", "action-risk", "compliance-readiness", "operational-health", "portfolio-team",
];
const browser = await chromium.launch({ headless: true });
console.log(`Accessibility browser: Chromium ${browser.version()}; platform: ${process.platform}`);
const failures = [];

async function checkDuplicateAttributeBoundary() {
  const temporary = await fs.mkdtemp(path.join(await fs.realpath(os.tmpdir()), "reportkit-duplicate-"));
  const contexts = [];
  async function offlineContext() {
    const context = await browser.newContext({ serviceWorkers: "block" });
    contexts.push(context);
    const requests = new Set();
    await context.route("**/*", async (route) => {
      if (["file:", "data:", "about:"].includes(new URL(route.request().url()).protocol)) {
        await route.continue();
      } else {
        requests.add(route.request().url());
        await route.abort("blockedbyclient");
      }
    });
    return { context, requests };
  }
  async function openValidated(site, page) {
    const result = spawnSync(process.env.REPORTKIT_PYTHON ?? "python",
      ["-B", path.join(root, "scripts", "validate"), site, "--kind", "site"],
      { encoding: "utf8" });
    if (result.error) throw result.error;
    if (![0, 1].includes(result.status)) throw new Error(`Validator failed: ${result.stderr}`);
    const report = JSON.parse(result.stdout);
    if ((result.status === 0) !== (report.errors.length === 0)) {
      throw new Error("Validator exit status disagrees with its structured errors.");
    }
    if (result.status === 0) {
      await page.goto(pathToFileURL(path.join(site, "index.html")).href, { waitUntil: "networkidle" });
    }
    return report;
  }
  try {
    const site = path.join(temporary, "site");
    await fs.cp(path.join(root, "examples", "operational-snapshot", "generated", "executive-health"),
      site, { recursive: true });
    const gated = await offlineContext();
    const baselinePage = await gated.context.newPage();
    const baseline = await openValidated(site, baselinePage);
    if (baseline.errors.length || gated.requests.size || baselinePage.url() === "about:blank") {
      throw new Error("Clean baseline must pass validation, open, and make zero external requests.");
    }
    await baselinePage.close();

    const index = path.join(site, "index.html");
    const original = await fs.readFile(index, "utf8");
    const csp = original.match(/<meta http-equiv="Content-Security-Policy" content="([^"]+)">/);
    if (!csp) throw new Error("Duplicate-attribute fixture requires the generated CSP.");
    const tracker = "https://tracker.invalid/duplicate.png";
    const malicious = original.replace(csp[0],
      `<meta http-equiv="Content-Security-Policy" content="default-src *; img-src *" CONTENT="${csp[1]}">`)
      .replace("</body>", `<img id="duplicate-probe" src="${tracker}" SRC="index.html" alt=""></body>`);
    await fs.writeFile(index, malicious);
    const manifestPath = path.join(site, "report-manifest.json");
    const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
    manifest.reproducibility.artifactHashes["index.html"] =
      `sha256:${createHash("sha256").update(await fs.readFile(index)).digest("hex")}`;
    await fs.writeFile(manifestPath, JSON.stringify(manifest));

    // Negative control: demonstrate browser first-value behavior, without sending traffic.
    const control = await offlineContext();
    const controlPage = await control.context.newPage();
    await controlPage.setContent(malicious, { waitUntil: "networkidle" });
    const interpreted = await controlPage.evaluate(() => ({
      csp: document.querySelector('meta[http-equiv="Content-Security-Policy"]').content,
      src: document.querySelector("#duplicate-probe").getAttribute("src"),
    }));
    if (interpreted.csp !== "default-src *; img-src *" ||
        interpreted.src !== tracker || !control.requests.has(tracker)) {
      throw new Error("Duplicate-attribute control did not exercise the browser parser disagreement.");
    }
    await controlPage.close();

    const rejectedPage = await gated.context.newPage();
    const report = await openValidated(site, rejectedPage);
    if (report.status !== "failed" ||
        report.errors.filter((issue) => issue.code === "duplicate-html-attribute").length !== 2 ||
        report.errors.some((issue) => issue.code.startsWith("identity-")) ||
        gated.requests.size || rejectedPage.url() !== "about:blank") {
      throw new Error("Rehashed duplicate-attribute site must fail before opening, with zero external requests.");
    }
    console.log("PASS duplicate-attribute boundary: browser control blocked; rehashed site rejected before opening; zero gated external requests.");
  } finally {
    for (const context of contexts) await context.close();
    await fs.rm(temporary, { recursive: true, force: true });
  }
}

try {
  await checkDuplicateAttributeBoundary();
  const adversarialContext = await browser.newContext({ serviceWorkers: "block" });
  const adversarialRequests = new Set();
  await adversarialContext.route("**/*", async (route) => {
    const url = route.request().url();
    if (!["about:", "data:"].includes(new URL(url).protocol)) {
      adversarialRequests.add(url);
      await route.abort("blockedbyclient");
    } else {
      await route.continue();
    }
  });
  const adversarialPage = await adversarialContext.newPage();
  await adversarialPage.setContent(
    '<style>@import "https://reportkit.invalid/pre-csp.css";</style>' +
    `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">`,
  );
  await adversarialPage.waitForTimeout(100);
  await adversarialContext.close();
  if (![...adversarialRequests].some((url) => url.includes("reportkit.invalid/pre-csp.css"))) {
    failures.push("Adversarial CSP-order fixture did not exercise the browser's pre-CSP request behavior.");
  } else {
    console.log("PASS adversarial CSP-order fixture: pre-CSP CSS request observed and blocked by the test harness.");
  }

  for (const example of examples) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 },
      deviceScaleFactor: 1,
      colorScheme: "light",
      reducedMotion: "reduce",
      serviceWorkers: "block",
    });
    const externalRequests = new Set();
    await context.route("**/*", async (route) => {
      const url = route.request().url();
      if (!["file:", "data:"].includes(new URL(url).protocol)) {
        externalRequests.add(url);
        await route.abort("blockedbyclient");
      } else {
        await route.continue();
      }
    });
    await context.routeWebSocket("**/*", (socket) => {
      externalRequests.add(socket.url());
      socket.close();
    });
    const page = await context.newPage();
    try {
      const source = path.join(root, "examples", "operational-snapshot", "generated", example, "index.html");
      await fs.access(source);
      await page.goto(pathToFileURL(source).href, { waitUntil: "networkidle" });
      await page.evaluate(() => document.fonts.ready);
      const issues = await page.evaluate(() => {
        const errors = [];
        const visible = (element) => {
          const style = getComputedStyle(element);
          return element.getClientRects().length > 0 &&
            style.visibility === "visible" && Number(style.opacity) > 0;
        };
        const headings = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].filter(visible);
        if (headings.filter((heading) => heading.tagName === "H1").length !== 1) {
          errors.push("Expected exactly one visible h1.");
        }
        const main = [...document.querySelectorAll("main,[role=main]")].filter(visible);
        if (main.length !== 1) errors.push("Expected exactly one visible main landmark.");
        let previous = 0;
        for (const heading of headings) {
          const level = Number(heading.tagName.slice(1));
          if (!heading.textContent.trim()) errors.push("Empty heading.");
          if (level > previous + 1) errors.push(`Heading level skipped: h${previous} to h${level}.`);
          previous = level;
        }
        for (const image of document.querySelectorAll("img")) {
          if (!image.hasAttribute("alt")) errors.push("Image lacks an explicit alt attribute.");
        }
        return errors;
      });

      const links = page.locator("a[href]:visible");
      const linkCount = await links.count();
      const namedLinks = await page.getByRole("link", { name: /\S/ }).count();
      if (namedLinks !== linkCount) issues.push("Every visible link must have a nonempty accessible name.");
      const candidates = await page.locator(
        "a[href],button,input,select,textarea,summary,[tabindex]",
      ).count();
      const reached = new Set();
      // Tab from the initial document focus; never programmatically focus a link.
      for (let step = 0; step < candidates + 2 && reached.size < linkCount; step++) {
        await page.keyboard.press("Tab");
        const focused = await page.evaluate(() => {
          const element = document.activeElement;
          const links = [...document.querySelectorAll("a[href]")].filter((link) => {
            const style = getComputedStyle(link);
            return link.getClientRects().length > 0 && style.visibility === "visible";
          });
          const index = links.indexOf(element);
          if (index === -1) return { index };
          const style = getComputedStyle(element);
          const rect = element.getBoundingClientRect();
          const color = style.outlineColor;
          const transparent = color === "transparent" || /,\s*0\s*\)$/.test(color);
          const outlined = !["none", "hidden"].includes(style.outlineStyle) &&
            Number.parseFloat(style.outlineWidth) >= 2 && !transparent;
          let opaque = true;
          for (let node = element; node; node = node.parentElement) {
            if (Number(getComputedStyle(node).opacity) === 0) opaque = false;
          }
          const inViewport = rect.width > 0 && rect.height > 0 &&
            rect.bottom > 0 && rect.right > 0 && rect.top < innerHeight && rect.left < innerWidth;
          const hit = document.elementFromPoint(
            Math.max(0, Math.min(innerWidth - 1, rect.left + rect.width / 2)),
            Math.max(0, Math.min(innerHeight - 1, rect.top + rect.height / 2)),
          );
          return {
            index,
            label: element.textContent.trim().slice(0, 80),
            visibleFocus: element.matches(":focus-visible") && outlined && opaque &&
              inViewport && (hit === element || element.contains(hit)),
          };
        });
        if (focused.index !== -1) {
          reached.add(focused.index);
          if (!focused.visibleFocus) {
            issues.push(`Keyboard link lacks visible outline focus: ${focused.label}`);
          }
        }
      }
      if (reached.size !== linkCount) {
        issues.push(`Keyboard reached ${reached.size} of ${linkCount} visible links.`);
      }
      if (externalRequests.size) issues.push(`External requests blocked: ${[...externalRequests].join(", ")}`);
      if (issues.length) failures.push(`${example}:\n  ${issues.join("\n  ")}`);
      else console.log(`PASS ${example}: headings, main, names, alts, keyboard focus; no external requests.`);
    } catch (error) {
      failures.push(`${example}: ${error.message}`);
    } finally {
      await context.close();
    }
  }
} finally {
  await browser.close();
}
if (failures.length) throw new Error(`Accessibility smoke checks failed:\n${failures.join("\n")}`);
console.log("Basic accessibility smoke checks passed; not a WCAG certification or contrast audit.");
