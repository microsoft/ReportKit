import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawn } from "node:child_process";
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";

// Authoring tool only: narration uses Windows SAPI, never a network speech service.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const modules = process.env.REPORTKIT_VISUAL_NODE_MODULES ??
  path.join(root, "tests", "visual", "node_modules");
const require = createRequire(import.meta.url);
const ffmpeg = require(path.join(modules, "ffmpeg-static"));
const { chromium } = await import(pathToFileURL(path.join(modules, "playwright", "index.mjs")).href);
const destination = process.argv[2];
if (!destination) throw new Error("Supply a new output directory for the narrated video.");
if (process.platform !== "win32") throw new Error("Narration production requires Windows SAPI.");
const output = path.resolve(destination);
await fs.mkdir(output, { recursive: false });
const temporary = await fs.mkdtemp(path.join(os.tmpdir(), "reportkit-narrated-"));
const scenes = [
  {
    id: "01-introduction", seconds: 8,
    narration: "Your operational data already tells a story. Report Kit turns it into a report people can actually use.",
    eyebrow: "FROM DATA TO DECISIONS", title: "Make the facts<br>easy to act on.",
    copy: "Durable, audience-specific static reports.",
    label: "Executive Health / generated report", kind: "hero",
  },
  {
    id: "02-guided-flow", seconds: 10,
    narration: "Start with the decision your audience needs to make. Choose Executive Health, add a data snapshot, then build and review.",
    eyebrow: "A GUIDED START", title: "One decision.<br>A clear next step.",
    copy: "Guided in your AI assistant.<br>Review before you share.",
    label: "Skill-led workflow / not a web application", kind: "guided",
  },
  {
    id: "03-executive-health", seconds: 11,
    narration: "See portfolio health, freshness, trends, and records that need attention. This report is generated from four hundred and one synthetic records.",
    eyebrow: "EXECUTIVE HEALTH", title: "See what<br>needs attention.",
    copy: "Status. Freshness. Trends.<br>The context behind the numbers.",
    label: "Actual generated output / public synthetic sample", kind: "report",
  },
  {
    id: "04-validation", seconds: 10,
    narration: "Validation checks your data and the finished report. Warnings stay visible. Share portable pages, with no backend or required scripts.",
    eyebrow: "VALIDATE BEFORE SHARING", title: "Portable output.<br>Visible checks.",
    copy: "Validate the model.<br>Validate the exact generated site.",
    label: "Actual Executive Health validation result", kind: "validation",
  },
  {
    id: "05-designs", seconds: 10,
    narration: "Need a different perspective? Explore four additional report designs, or build with a locked, single page declarative template.",
    eyebrow: "DESIGNED FOR THE AUDIENCE", title: "Different readers.<br>Different decisions.",
    copy: "Four additional static previews.<br>Custom declarative builds available.",
    label: "Four design previews / built-in renderers not connected", kind: "designs",
  },
  {
    id: "06-close", seconds: 11,
    narration: "One model, five report designs, one generated today. Explore Report Kit on GitHub, and start with the public sample.",
    eyebrow: "REPORTKIT", title: "One model.<br>Five report designs.<br>One generated today.",
    copy: "Explore the project.<br>Start with the public sample.",
    label: "Experimental Hack Week preview / not a technical release", kind: "close",
  },
];

function run(executable, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(executable, args, { stdio: ["ignore", "pipe", "pipe"] });
    let text = "";
    child.stdout.on("data", (chunk) => { text += chunk; });
    child.stderr.on("data", (chunk) => { text += chunk; });
    child.on("error", reject);
    child.on("close", (code) => code === 0 ? resolve(text) : reject(new Error(text)));
  });
}
const escape = (value) => String(value).replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
async function image(name) {
  const bytes = await fs.readFile(path.join(root, "docs", "assets", "screenshots", name));
  return `data:image/png;base64,${bytes.toString("base64")}`;
}
function waveDuration(bytes) {
  if (bytes.toString("ascii", 0, 4) !== "RIFF") throw new Error("Expected PCM WAV narration.");
  let rate, size;
  for (let position = 12; position + 8 <= bytes.length;) {
    const id = bytes.toString("ascii", position, position + 4);
    const length = bytes.readUInt32LE(position + 4);
    if (id === "fmt ") rate = bytes.readUInt32LE(position + 16);
    if (id === "data") size = length;
    position += 8 + length + (length % 2);
  }
  if (!rate || !size) throw new Error("Missing narration audio data.");
  return size / rate;
}
function timestamp(seconds) {
  const ms = Math.round(seconds * 1000);
  return `${String(Math.floor(ms / 3600000)).padStart(2, "0")}:` +
    `${String(Math.floor(ms / 60000) % 60).padStart(2, "0")}:` +
    `${String(Math.floor(ms / 1000) % 60).padStart(2, "0")},${String(ms % 1000).padStart(3, "0")}`;
}

let browser;
try {
  const manifest = JSON.parse(await fs.readFile(path.join(root,
    "examples", "operational-snapshot", "generated", "executive-health", "report-manifest.json"), "utf8"));
  const validation = JSON.parse(await fs.readFile(path.join(root,
    "examples", "operational-snapshot", "generated", "executive-health", "validation-report.json"), "utf8"));
  if (manifest.itemCount !== 401 || validation.status !== "passed" || validation.errors.length) {
    throw new Error("The narration requires the validated 401-record Executive Health sample.");
  }
  const screenshots = {
    executive: await image("executive-health-hero.png"),
    action: await image("action-risk-hero.png"),
    portfolio: await image("portfolio-team-hero.png"),
    operational: await image("operational-health-hero.png"),
    compliance: await image("compliance-readiness-hero.png"),
  };
  const panel = (scene) => {
    if (scene.kind === "guided") return `<div class="assistant panel">
      <div class="tiny">REPORTKIT / GUIDED IN YOUR AI ASSISTANT</div>
      <h2>From a question<br>to a validated report.</h2>
      <div class="step active"><b>01</b><div>Choose a template<small>Executive Health</small></div><i>SELECTED</i></div>
      <div class="step"><b>02</b><div>Add your data<small>Included public sample</small></div></div>
      <div class="step"><b>03</b><div>Build and review<small>Generated HTML + validation</small></div></div>
      <div class="step"><b>04</b><div>Export or publish<small>Currently returns files for manual copying</small></div></div>
      <div class="note">Nothing is published without your approval.</div></div>`;
    if (scene.kind === "validation") return `<div class="panel validation">
      <div class="tiny">EXECUTIVE HEALTH / GENERATED ARTIFACT</div>
      <div class="pass"><span>&#10003;</span> Validation passed</div>
      <div class="counters"><div><b>${validation.errors.length}</b><small>Errors</small></div>
      <div><b>${validation.warnings.length}</b><small>Warnings</small></div>
      <div><b>${manifest.itemCount}</b><small>Canonical items</small></div></div>
      <div class="file">index.html <span>Static report</span></div>
      <div class="file">report-manifest.json <span>Identity + counts</span></div>
      <div class="file">validation-report.json <span>Checks + warnings</span></div>
      <div class="note">Warnings remain visible when present.</div>
      <div class="chips"><span>No backend</span><span>No required JavaScript</span></div></div>`;
    if (scene.kind === "designs") return `<div class="design-grid">${[
      ["Action &amp; Risk", screenshots.action], ["Portfolio / Team", screenshots.portfolio],
      ["Operational Health", screenshots.operational], ["Compliance / Readiness", screenshots.compliance],
    ].map(([name, source]) => `<div class="design"><img src="${source}"><div><b>${name}</b><span>STATIC PREVIEW</span></div></div>`).join("")}</div>`;
    if (scene.kind === "close") return `<div class="end-panel">
      <div class="logo large">R</div><h2>ReportKit</h2><p>From operational data<br>to a durable report.</p>
      <div class="url">github.com/microsoft/ReportKit</div>
      <div class="end-tags">Open source <i></i> Static-first <i></i> Skill-led</div></div>`;
    return `<div class="browser"><div class="browser-bar"><i></i><i></i><i></i><span>ReportKit / Executive Health</span>
      <b>PUBLIC SAMPLE</b></div><img src="${screenshots.executive}"></div>
      ${scene.kind === "report" ? `<div class="report-strip"><span><b>401</b> canonical records</span><span><b>1</b> generated page</span><span><b>0</b> validation errors</span></div>` : ""}`;
  };
  const html = (scene, index) => `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;width:1920px;height:1080px;overflow:hidden;
    color:#f6f9fe;background:#061629;font-family:"Segoe UI",Arial,sans-serif}
    body:before{content:"";position:absolute;width:1400px;height:1400px;border-radius:50%;right:-460px;top:-410px;
    background:radial-gradient(circle,#16446a88,transparent 68%)}.accent{position:absolute;top:0;left:0;height:7px;width:1920px;
    background:linear-gradient(90deg,#5bc8ff,#3bd8b0 65%,#102c46)}.top{position:absolute;left:84px;right:84px;top:54px;display:flex;
    justify-content:space-between;align-items:center;font-size:23px;letter-spacing:.05em}.brand{display:flex;align-items:center;gap:15px;font-weight:750}
    .logo{width:42px;height:42px;border-radius:11px;background:#68d4ff;color:#08233e;display:grid;place-items:center;font-size:27px;font-weight:850}
    .top-note{font-size:17px;color:#9db7ce;letter-spacing:.1em}.copy{position:absolute;left:84px;top:246px;width:660px}
    .eyebrow{font-size:18px;letter-spacing:.17em;color:#70d7ff;font-weight:750;margin-bottom:30px}
    h1{font-size:${scene.kind === "close" ? 64 : 74}px;line-height:1.07;letter-spacing:-2.6px;margin:0 0 32px;font-weight:720}
    .lead{font-size:27px;line-height:1.55;color:#afc5d8;margin:0}.right{position:absolute;left:790px;right:84px;top:186px;height:740px;display:flex;flex-direction:column;justify-content:center}
    .browser{background:white;border:1px solid #7993ab;border-radius:17px;overflow:hidden;box-shadow:0 30px 80px #0007}
    .browser-bar{height:42px;display:flex;align-items:center;gap:8px;padding:0 18px;background:#e5edf4;color:#54697b;font-size:13px}
    .browser-bar i{width:8px;height:8px;background:#aebdca;border-radius:50%}.browser-bar span{margin-left:14px}.browser-bar b{margin-left:auto;font-size:10px}
    .browser img{display:block;width:100%}.report-strip{display:flex;justify-content:space-between;padding:25px 4px 0;color:#adc4d7;font-size:17px}
    .report-strip b{font-size:25px;color:#fff;margin-right:6px}.panel{padding:40px 44px;background:linear-gradient(135deg,#132e48,#0c2238);
    border:1px solid #31526d;border-radius:24px;box-shadow:0 24px 80px #0005}.tiny{font-size:15px;letter-spacing:.11em;color:#87c6e8}
    h2{font-size:38px;line-height:1.2;margin:25px 0 28px}.step{padding:19px 20px;display:flex;gap:22px;align-items:center;border-top:1px solid #2d465e;font-size:24px}
    .step b{color:#71cff6;font-size:20px}.step small{display:block;font-size:17px;color:#a4bed3;margin-top:6px}.step i{margin-left:auto;font-size:13px;color:#7ee3bc;font-style:normal}
    .active{background:#133951;border-radius:12px;border:1px solid #347294}.note{font-size:18px;color:#aac7da;margin-top:27px}
    .pass{margin:35px 0;font-size:41px;font-weight:700}.pass span{color:#6fe6b9;margin-right:10px}.counters{display:grid;grid-template-columns:repeat(3,1fr);gap:15px;margin-bottom:32px}
    .counters div{background:#071a2d;border:1px solid #26475e;padding:20px;border-radius:12px}.counters b{display:block;font-size:48px;font-weight:650}
    .counters small{font-size:16px;color:#a2c0d6}.file{padding:21px 0;border-top:1px solid #2c4862;font-size:21px}.file span{float:right;color:#9fbcd3;font-size:18px}
    .chips{display:flex;gap:12px;margin-top:23px}.chips span{border:1px solid #3c667e;border-radius:30px;padding:9px 17px;font-size:17px;color:#9cdecf}
    .design-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px}.design{overflow:hidden;border:1px solid #3d5870;border-radius:14px;background:#10273e}
    .design img{width:100%;height:247px;object-fit:cover;object-position:top;display:block}.design>div{padding:17px 20px}
    .design b{display:block;font-size:22px}.design span{display:block;font-size:12px;letter-spacing:.14em;color:#e9bc74;margin-top:7px}
    .end-panel{text-align:center}.large{width:96px;height:96px;border-radius:24px;font-size:64px;margin:0 auto 24px}.end-panel h2{font-size:65px;letter-spacing:-2px;margin:0}
    .end-panel p{font-size:27px;color:#aac5d9;line-height:1.5}.url{font-size:29px;background:#173850;border:1px solid #3c7593;border-radius:12px;padding:24px 18px;margin-top:34px}
    .end-tags{color:#87b5cc;font-size:20px;margin-top:26px}.end-tags i:after{content:" / ";padding:0 15px;color:#4a7791}
    footer{position:absolute;bottom:56px;left:84px;right:84px;border-top:1px solid #284057;padding-top:22px;display:flex;justify-content:space-between;align-items:center}
    footer span{font-size:17px;color:#8eabc3}.dots{display:flex;gap:10px}.dots i{width:32px;height:4px;border-radius:2px;background:#2b465f}
    .dots i.current{background:#70d7ff}
    </style></head><body><div class="accent"></div><div class="top"><div class="brand"><div class="logo">R</div>ReportKit</div>
    <span class="top-note">EXPERIMENTAL HACK WEEK PREVIEW</span></div><div class="copy"><div class="eyebrow">${scene.eyebrow}</div>
    <h1>${scene.title}</h1><p class="lead">${scene.copy}</p></div><div class="right">${panel(scene)}</div>
    <footer><span>${escape(scene.label)}</span><div class="dots">${scenes.map((_, i) => `<i class="${i === index ? "current" : ""}"></i>`).join("")}</div></footer></body></html>`;

  const timeline = path.join(temporary, "timeline.json");
  await fs.writeFile(timeline, JSON.stringify(scenes));
  await run("powershell.exe", ["-NoProfile", "-File", path.join(root, "scripts", "create-video-narration.ps1"),
    "-Timeline", timeline, "-OutputDirectory", temporary]);
  for (const scene of scenes) {
    const duration = waveDuration(await fs.readFile(path.join(temporary, `${scene.id}.wav`)));
    if (duration / (scene.seconds - 1.1) > 1.25) {
      throw new Error(`Narration is too long for ${scene.id}: ${duration}s.`);
    }
  }
  browser = await chromium.launch({ channel: "msedge", headless: true });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const transition = 0.4;
  let elapsed = 0, subtitleIndex = 1;
  const captions = [], details = [];
  for (const [index, scene] of scenes.entries()) {
    await page.setContent(html(scene, index), { waitUntil: "load" });
    await page.evaluate(() => document.fonts.ready);
    const overflows = await page.evaluate(() => {
      const left = document.querySelector(".copy").getBoundingClientRect();
      const right = document.querySelector(".right").getBoundingClientRect();
      const footer = document.querySelector("footer").getBoundingClientRect();
      return left.right >= right.left || left.bottom >= footer.top ||
        [...document.querySelector(".right").children].some((child) => child.getBoundingClientRect().bottom >= footer.top);
    });
    if (overflows) throw new Error(`Scene layout overflow: ${scene.id}`);
    const still = path.join(temporary, `${scene.id}.png`);
    await page.screenshot({ path: still });
    await fs.copyFile(still, path.join(output, `${scene.id}.png`));
    const wav = path.join(temporary, `${scene.id}.wav`);
    const spoken = waveDuration(await fs.readFile(wav));
    const available = scene.seconds - 1.1;
    const tempo = Math.max(1, spoken / available);
    if (tempo > 1.25) throw new Error(`Narration is too long for ${scene.id}: ${spoken}s.`);
    details.push({ id: scene.id, startsAt: elapsed, seconds: scene.seconds, spokenSeconds: spoken, tempo });
    const sentences = scene.narration.match(/[^.!?]+[.!?]+/g).map((s) => s.trim());
    let sentenceStart = elapsed + 0.45;
    for (const sentence of sentences) {
      const duration = spoken / tempo * sentence.length / sentences.reduce((sum, s) => sum + s.length, 0);
      captions.push(`${subtitleIndex++}\n${timestamp(sentenceStart)} --> ${timestamp(sentenceStart + duration)}\n${sentence.replaceAll("Report Kit", "ReportKit")}\n`);
      sentenceStart += duration;
    }
    // Each visual extends across the next crossfade; audio retains the exact scene duration.
    const visualSeconds = scene.seconds + (index < scenes.length - 1 ? transition : 0);
    const timedAudio = path.join(temporary, `${scene.id}-timed.wav`);
    await run(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", "-i", wav, "-af",
      `atempo=${tempo},aresample=48000,asetpts=N/SR/TB,adelay=450,` +
      `apad=whole_len=${scene.seconds * 48000},atrim=end_sample=${scene.seconds * 48000},asetpts=N/SR/TB`,
      "-ac", "1", timedAudio]);
    if (Math.abs(waveDuration(await fs.readFile(timedAudio)) - scene.seconds) > 0.001) {
      throw new Error(`Audio sample-count mismatch: ${scene.id}.`);
    }
    await run(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y",
      "-loop", "1", "-framerate", "30", "-i", still, "-t", String(visualSeconds),
      "-vf", "scale=1958:1102,crop=1920:1080:x='19+8*sin(t/5)':y='11+5*sin(t/6)',setsar=1",
      "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
      path.join(temporary, `${scene.id}.mp4`)]);
    elapsed += scene.seconds;
    console.log(`Produced ${scene.id}: ${scene.seconds}s, narration ${spoken.toFixed(2)}s.`);
  }
  if (elapsed !== 60) throw new Error("Video timeline must equal exactly 60 seconds.");
  const subtitles = path.join(output, "reportkit-60-second.srt");
  await fs.writeFile(subtitles, captions.join("\n"));
  const narrationTimeline = path.join(temporary, "narration-timeline.wav");
  await run(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y",
    ...scenes.flatMap((scene) => ["-i", path.join(temporary, `${scene.id}-timed.wav`)]),
    "-filter_complex", `${scenes.map((_, i) => `[${i}:a]`).join("")}concat=n=6:v=0:a=1[a]`,
    "-map", "[a]", narrationTimeline]);
  const narrationSeconds = waveDuration(await fs.readFile(narrationTimeline));
  if (Math.abs(narrationSeconds - 60) > 0.01) throw new Error(`Audio timeline is ${narrationSeconds}s, not 60s.`);
  const measured = await run(ffmpeg, ["-hide_banner", "-nostats", "-i", narrationTimeline,
    "-af", "loudnorm=I=-16:TP=-2:LRA=9:print_format=json", "-f", "null", "-"]);
  const loudness = JSON.parse(measured.slice(measured.lastIndexOf("{")));
  const inputs = scenes.flatMap((scene) => ["-i", path.join(temporary, `${scene.id}.mp4`)]);
  inputs.push("-i", narrationTimeline, "-i", subtitles);
  const filters = [];
  let offset = 0;
  for (let i = 1; i < scenes.length; i++) {
    offset += scenes[i - 1].seconds;
    filters.push(`[${i === 1 ? "0:v" : `v${i - 1}`}][${i}:v]xfade=transition=fade:duration=${transition}:offset=${offset}[v${i}]`);
  }
  filters.push("[v5]fade=t=in:st=0:d=0.35,fade=t=out:st=59.4:d=0.6[v]");
  filters.push("[6:a]loudnorm=I=-16:TP=-2:LRA=9:linear=true:" +
    `measured_I=${loudness.input_i}:measured_TP=${loudness.input_tp}:` +
    `measured_LRA=${loudness.input_lra}:measured_thresh=${loudness.input_thresh}:offset=${loudness.target_offset},` +
    "aresample=48000,apad,atrim=duration=60,afade=t=out:st=59.6:d=0.4[a]");
  await run(ffmpeg, ["-hide_banner", "-loglevel", "error", "-y", ...inputs,
    "-filter_complex_threads", "1", "-filter_complex", filters.join(";"),
    "-map", "[v]", "-map", "[a]", "-map", "7:s:0", "-t", "60",
    "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-c:s", "mov_text", "-metadata:s:s:0", "language=eng",
    "-metadata", "title=ReportKit - From data to decisions",
    "-metadata", "comment=Local synthetic narration: Microsoft Zira. Experimental Hack Week preview.",
    "-movflags", "+faststart", path.join(output, "reportkit-60-second-narrated.mp4")]);
  await fs.writeFile(path.join(output, "production.json"), JSON.stringify({
    durationSeconds: elapsed, width: 1920, height: 1080, framesPerSecond: 30,
    narration: "Microsoft Zira Desktop (local synthetic English voice)",
    captions: "Embedded English selectable captions and sidecar SRT; sentence timings are approximate.",
    scenes: scenes.map((scene, i) => ({ ...details[i], narration: scene.narration })),
  }, null, 2) + "\n");
  console.log(`Created ${path.join(output, "reportkit-60-second-narrated.mp4")}`);
} finally {
  if (browser) await browser.close();
  await fs.rm(temporary, { recursive: true, force: true });
}
