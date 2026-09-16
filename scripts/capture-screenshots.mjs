import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, "..");
const visualNodeModules =
  process.env.REPORTKIT_VISUAL_NODE_MODULES ??
  path.join(root, "tests", "visual", "node_modules");
const { chromium } = await import(
  pathToFileURL(path.join(visualNodeModules, "playwright", "index.mjs")).href
);
const contract = JSON.parse(
  await fs.readFile(path.join(root, "tests", "visual", "screenshot-contract.json"), "utf8"),
);
const outputRoot = path.join(root, "docs", "assets", "screenshots");
await fs.mkdir(outputRoot, { recursive: true });

const channel = process.env.REPORTKIT_SCREENSHOT_CHANNEL ?? "chromium";
if (!["chromium", "msedge"].includes(channel)) {
  throw new Error(`Unsupported screenshot browser channel: ${channel}`);
}
const browser = await chromium.launch({
  ...(channel === "msedge" ? { channel } : {}),
  headless: true,
});
console.log(`Screenshot browser: ${channel} ${browser.version()}; platform: ${process.platform}`);

try {
  for (const capture of contract.captures) {
    const source = path.join(root, capture.page);
    await fs.access(source);
    const target = path.join(outputRoot, capture.name);
    await fs.mkdir(path.dirname(target), { recursive: true });
    const page = await browser.newPage({
      viewport: { width: capture.width, height: capture.height },
      deviceScaleFactor: contract.defaults.deviceScaleFactor,
      colorScheme: contract.defaults.colorScheme,
      reducedMotion: contract.defaults.reducedMotion,
    });
    await page.goto(pathToFileURL(source).href, { waitUntil: "load" });
    await page.addStyleTag({
      content: "*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}",
    });
    await page.evaluate(() => document.fonts?.ready);
    await page.waitForTimeout(100);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
    );
    if (overflow) {
      throw new Error(`Horizontal overflow detected for ${capture.page} at ${capture.width}px`);
    }
    await page.screenshot({
      path: target,
      fullPage: capture.fullPage,
      animations: "disabled",
      type: "png",
    });
    await page.close();
    console.log(`Captured ${capture.name}`);
  }
} finally {
  await browser.close();
}
