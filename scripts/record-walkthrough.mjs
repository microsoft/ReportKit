import fs from "node:fs/promises";
import path from "node:path";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

const require = createRequire(import.meta.url);
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(scriptDir, "..");
const visualNodeModules =
  process.env.REPORTKIT_VISUAL_NODE_MODULES ??
  path.join(root, "tests", "visual", "node_modules");
const { chromium } = await import(
  pathToFileURL(path.join(visualNodeModules, "playwright", "index.mjs")).href
);
const ffmpegPath = require(path.join(visualNodeModules, "ffmpeg-static"));
const temporaryDir = path.join(root, "tests", "visual", ".walkthrough-video");
const output = path.join(root, "docs", "assets", "reportkit-walkthrough.mp4");

await fs.rm(temporaryDir, { recursive: true, force: true });
await fs.mkdir(temporaryDir, { recursive: true });

let browser;
try {
  browser = await chromium.launch({ channel: "msedge", headless: true });
} catch {
  browser = await chromium.launch({ headless: true });
}

try {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 1,
    colorScheme: "light",
    recordVideo: {
      dir: temporaryDir,
      size: { width: 1280, height: 720 },
    },
  });
  const page = await context.newPage();
  const video = page.video();
  await page.goto(pathToFileURL(path.join(root, "showcase", "walkthrough.html")).href);
  await page.evaluate(() => document.fonts?.ready);
  await page.waitForTimeout(35_000);
  await page.close();
  const recordedVideo = await video.path();
  await context.close();

  await new Promise((resolve, reject) => {
    const ffmpeg = spawn(
      ffmpegPath,
      [
        "-y",
        "-i",
        recordedVideo,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        output,
      ],
      { stdio: "inherit" },
    );
    ffmpeg.on("error", reject);
    ffmpeg.on("exit", (code) =>
      code === 0 ? resolve() : reject(new Error(`ffmpeg exited with code ${code}`)),
    );
  });
} finally {
  await browser.close();
  await fs.rm(temporaryDir, { recursive: true, force: true });
}

console.log(`Recorded ${path.relative(root, output)}`);
