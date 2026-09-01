#!/usr/bin/env node
/**
 * Brand & theme conformance audit — the Origin design rules, ENFORCED.
 *
 * Fails (exit 1) on the classes of drift that keep creeping back:
 *   1. Hardcoded slate/white utility classes in app components (the deleted compat
 *      shim's targets) — everything must use the semantic tokens.
 *   2. Tailwind palette colours anywhere in app components. Since the Soul Palette V2.1
 *      merge, colour comes from tokens only: status is ok/over/warn (a verified
 *      foreground+background pair that flips with the theme on its own), brand is
 *      primary/chart-N. A sky/emerald/red/amber/indigo/violet class is drift.
 *   3. Rotated axis labels (angle= on recharts axes) — axis text is flat, always.
 *   4. Raw hex colours in TSX outside the allowlist — colour comes from tokens.
 *
 * Allowlisted: the login page (intentionally fixed light + navy), ui/chart.tsx
 * (vendored shadcn primitive), and files that only reference hex inside comments.
 * Run: npm run audit:brand
 */
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const SRC = new URL("../src", import.meta.url).pathname;

const ALLOW_FILES = [
  "app/login/page.tsx", // fixed-light page with the navy brand panel
  "components/ui/chart.tsx", // vendored shadcn primitive
];

const files = [];
(function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(tsx|ts)$/.test(name) && !/\.test\./.test(name)) files.push(p);
  }
})(SRC);

const violations = [];

const SHIM_TARGETS =
  /(?<![\w:-])(text-white|text-slate-(?:100|200|300|400|500|600)|bg-white\/(?:5|10)|bg-slate-(?:950|900)\/(?:30|40|50|60|90|95)|border-white\/(?:5|10|15|20)|ring-white\/10)(?![\w/])/g;

// Any Tailwind palette colour is now drift: the tokens carry both themes themselves.
const PALETTE_CLASS =
  /(?<![\w:-])(?:dark:|group-hover:|hover:|focus:)*(?:text|bg|border|ring|from|via|to)-(sky|teal|amber|red|emerald|indigo|violet|cyan|rose|green|orange|purple|fuchsia|pink)-\d{2,3}(?:\/\d+)?(?![\w])/g;

const HEX_IN_CLASS = /(?:text|bg|border|ring|from|via|to)-\[#[0-9a-fA-F]{3,8}\]/g;

for (const file of files) {
  const rel = relative(SRC, file);
  if (ALLOW_FILES.includes(rel)) continue;
  const text = readFileSync(file, "utf8");
  const lines = text.split("\n");

  lines.forEach((line, i) => {
    if (/^\s*(\/\/|\*|\/\*)/.test(line)) return; // comments
    const where = `${rel}:${i + 1}`;

    for (const m of line.matchAll(SHIM_TARGETS)) {
      // text-white ON A COLORED FILL is correct (brand avatar, severity chips, logo
      // tiles): only flag it on theme surfaces, where it should be a token.
      const window = lines.slice(Math.max(0, i - 1), i + 3).join(" ");
      if (
        m[1] === "text-white" &&
        /bg-(?:brand|red-500|amber-500|emerald-500|sky-\d)|brand-logo|background: `?var\(|\$\{\w+(?:\.\w+)*\}/.test(window)
      ) {
        continue;
      }
      violations.push(`${where}  hardcoded theme class '${m[1]}' — use a semantic token class`);
    }
    for (const m of line.matchAll(PALETTE_CLASS)) {
      // paired is fine: a dark: sibling of the same hue somewhere on the line
      const hue = m[1];
      if (!line.includes(`dark:`) || !new RegExp(`dark:(?:group-hover:|hover:)?text-${hue}-`).test(line)) {
        violations.push(`${where}  un-paired light accent '${m[0]}' — write 'text-${hue}-600 dark:${m[0]}'`);
      }
    }
    if (/\bangle=\{?-?\d/.test(line)) {
      violations.push(`${where}  rotated axis label (angle=) — axis text is flat, truncate instead`);
    }
    for (const m of line.matchAll(HEX_IN_CLASS)) {
      violations.push(`${where}  raw hex in class '${m[0]}' — use a token (or extend the allowlist deliberately)`);
    }
  });
}

if (violations.length) {
  console.error(`brand audit: ${violations.length} violation(s)\n`);
  for (const v of violations) console.error("  " + v);
  process.exit(1);
}
console.log(`brand audit: clean (${files.length} files)`);
