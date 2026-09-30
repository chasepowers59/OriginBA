// Roll the crawl's per-page findings into one table: node e2e/summarize.mjs
import fs from "node:fs";
import path from "node:path";

const root = path.join(path.dirname(new URL(import.meta.url).pathname), ".out", "crawl");
const rows = [];
for (const vp of fs.readdirSync(root)) for (const org of fs.readdirSync(path.join(root, vp))) {
  for (const f of fs.readdirSync(path.join(root, vp, org)).filter((x) => x.endsWith(".json"))) {
    rows.push(JSON.parse(fs.readFileSync(path.join(root, vp, org, f), "utf8")));
  }
}
const hard = (r) => r.consoleErrors.length + r.failedRequests.length + r.brokenText.length + (r.horizontalOverflow > 1 ? 1 : 0);
rows.sort((a, b) => hard(b) - hard(a) || b.ms - a.ms);
console.log(`${rows.length} page visits; ${rows.filter((r) => hard(r)).length} with hard faults\n`);
for (const r of rows) {
  const bits = [];
  if (r.consoleErrors.length) bits.push(`console: ${[...new Set(r.consoleErrors)].slice(0, 2).join(" | ")}`);
  if (r.failedRequests.length) bits.push(`api: ${[...new Set(r.failedRequests)].slice(0, 3).join(" | ")}`);
  if (r.brokenText.length) bits.push(`text: ${r.brokenText.slice(0, 2).join(" | ")}`);
  if (r.horizontalOverflow > 1) bits.push(`overflow ${r.horizontalOverflow}px`);
  if (r.clipped.length) bits.push(`clipped ${r.clipped.length}: ${r.clipped.slice(0, 2).join(" | ")}`);
  if (r.unlabelled.length) bits.push(`unlabelled: ${r.unlabelled.join(", ")}`);
  if (r.emptyStates.length) bits.push(`says: ${[...new Set(r.emptyStates)].slice(0, 2).join(" | ")}`);
  if (r.ms > 8000) bits.push(`slow ${(r.ms / 1000).toFixed(1)}s`);
  if (bits.length) console.log(`${r.viewport.padEnd(7)} ${r.org.padEnd(10)} ${r.route}\n    ${bits.join("\n    ")}`);
}
