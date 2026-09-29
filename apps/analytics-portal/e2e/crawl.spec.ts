import { test, expect, type Page, type ConsoleMessage } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

/**
 * Crawl every page of the portal, per org and viewport, and record what an end user
 * would trip over: console errors, failed API calls, "NaN"/"undefined" on screen,
 * sideways scrolling, clipped text, unlabelled controls, and slow loads. Each page
 * writes a findings file and a full-page screenshot under e2e/.out (gitignored); the
 * test fails only on the hard faults (errors, failed calls, broken text, overflow).
 *
 *   npx playwright test e2e/crawl.spec.ts                      # every org below
 *   CRAWL_ORGS=demo25 npx playwright test e2e/crawl.spec.ts    # one org
 *   CRAWL_ROUTES=/,/reports npx playwright test e2e/crawl.spec.ts
 */

const API = process.env.PORTAL_API_URL ?? "http://127.0.0.1:8010";
const ORGS = (process.env.CRAWL_ORGS ?? "demo25,ellensburg").split(",");
const OUT = path.join(__dirname, ".out");

const STATIC = ["/", "/reports", "/dashboards", "/dashboard", "/dashboard/custom", "/build", "/database",
  "/data-quality", "/settings"];
const WORKSTREAMS = ["billing", "cashiering", "debt", "meter_ops", "field_ops", "customer_ops", "finance",
  "assets", "common"];
const CANVASES = JSON.parse(fs.readFileSync(path.join(__dirname, "../../../output/catalog_dbt.json"), "utf8"));
const CANVAS_IDS: string[] = Object.keys(CANVASES.snapshots ?? CANVASES);

function routes(): string[] {
  const all = [...STATIC, ...WORKSTREAMS.map((w) => `/workstream/${w}`), ...CANVAS_IDS.map((c) => `/explore/${c}`)];
  const only = process.env.CRAWL_ROUTES?.split(",");
  return only ? all.filter((r) => only.includes(r)) : all;
}

// Words that only reach the screen when a value was never formatted.
const BROKEN_TEXT = /\bNaN\b|\bundefined\b|\[object Object\]|\bInfinity\b/;

type Findings = {
  org: string; route: string; viewport: string; ms: number;
  consoleErrors: string[]; failedRequests: string[]; brokenText: string[];
  horizontalOverflow: number; widestElement: string; headerOverlaps: string[]; clipped: string[]; unlabelled: string[]; emptyStates: string[];
};

async function audit(page: Page) {
  const viewportWidth = page.viewportSize()!.width;
  return page.evaluate((viewportWidth) => {
    const vis = (el: Element) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none";
    };
    const label = (el: Element) => (el.textContent ?? "").trim().replace(/\s+/g, " ").slice(0, 80);
    const clipped: string[] = [];
    for (const el of Array.from(document.querySelectorAll("body *"))) {
      if (!vis(el) || !el.childNodes.length) continue;
      const box = el.getBoundingClientRect();
      if (box.width <= 2 || box.height <= 2) continue; // screen-reader-only text is 1px by design
      const s = getComputedStyle(el);
      const hides = ["hidden", "clip"].includes(s.overflowX) || ["hidden", "clip"].includes(s.overflow);
      if (!hides || s.textOverflow === "ellipsis") continue;
      const own = Array.from(el.childNodes).some((n) => n.nodeType === 3 && (n.textContent ?? "").trim());
      if (own && el.scrollWidth > el.clientWidth + 2) clipped.push(`${el.tagName.toLowerCase()}: ${label(el)}`);
    }
    const unlabelled = Array.from(document.querySelectorAll("button, a[href], input, select, textarea"))
      .filter((el) => vis(el))
      .filter((el) => {
        const aria = el.getAttribute("aria-label") || el.getAttribute("title") || el.getAttribute("aria-labelledby");
        const text = label(el);
        const input = el as HTMLInputElement;
        const labelled = input.id && document.querySelector(`label[for="${CSS.escape(input.id)}"]`);
        const placeholder = el.getAttribute("placeholder");
        return !aria && !text && !labelled && !placeholder && !el.closest("label");
      })
      .map((el) => `${el.tagName.toLowerCase()}${el.className ? "." + String(el.className).split(" ")[0] : ""}`);
    // Header controls drawn on top of each other (the menu button sat on the logo at 320px).
    const headerBoxes = Array.from(document.querySelectorAll("header a, header button, header summary, header select"))
      .filter((el) => vis(el) && el.getBoundingClientRect().top < 80)
      .map((el) => ({ el, r: el.getBoundingClientRect() }))
      .filter(({ el }) => !el.closest("details:not([open]) > div"));
    const headerOverlaps: string[] = [];
    for (let i = 0; i < headerBoxes.length; i++) for (let j = i + 1; j < headerBoxes.length; j++) {
      const a = headerBoxes[i], b = headerBoxes[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      const x = Math.min(a.r.right, b.r.right) - Math.max(a.r.left, b.r.left);
      const y = Math.min(a.r.bottom, b.r.bottom) - Math.max(a.r.top, b.r.top);
      if (x > 2 && y > 2) headerOverlaps.push(`${label(a.el) || a.el.getAttribute("aria-label")} / ${label(b.el) || b.el.getAttribute("aria-label")}`);
    }
    // Sideways overflow is the widest element's right edge past the viewport, not
    // documentElement.scrollWidth - innerWidth: on a phone the browser widens innerWidth to
    // fit the content, and a clipping ancestor hides it from scrollWidth, so a 347 px
    // explorer page at 320 measured 0. Skipped: content inside its own horizontal scroller
    // (reachable), anything wholly off-screen (a closed drawer), and empty decoration (the
    // home hero's blurred glow hangs 55 px past its clipping panel by design).
    const MEDIA = "img,svg,canvas,video,input,select,textarea,button";
    const hasContent = (el: Element) => Boolean(label(el)) || el.matches(MEDIA) || Boolean(el.querySelector(MEDIA));
    const inScroller = (el: Element) => {
      for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
        if (["auto", "scroll"].includes(getComputedStyle(p).overflowX)) return true;
      }
      return false;
    };
    let widestRight = 0;
    let widestElement = "";
    for (const el of Array.from(document.querySelectorAll("body *"))) {
      if (!vis(el)) continue;
      const r = el.getBoundingClientRect();
      if (r.right <= widestRight || r.left >= viewportWidth || r.right <= 0) continue;
      if (!hasContent(el) || inScroller(el)) continue;
      widestRight = r.right;
      widestElement = `${el.tagName.toLowerCase()}: ${label(el)}`;
    }
    const text = document.body.innerText;
    const emptyStates = (text.match(/^.*\b(no data|no rows|nothing to show|no results|not available|could not|failed|error)\b.*$/gim) ?? [])
      .map((l) => l.trim()).slice(0, 12);
    return {
      overflow: Math.ceil(widestRight) - viewportWidth,
      widestElement,
      clipped: clipped.slice(0, 20),
      unlabelled: Array.from(new Set(unlabelled)).slice(0, 20),
      emptyStates,
      headerOverlaps,
      text,
    };
  }, viewportWidth);
}

for (const org of ORGS) {
  test.describe(`org ${org}`, () => {
    for (const route of routes()) {
      test(`${route}`, async ({ page, context }, info) => {
        await context.addCookies([{ name: "portal_active_organization", value: org, url: info.project.use.baseURL! }]);
        const consoleErrors: string[] = [];
        const failedRequests: string[] = [];
        page.on("console", (m: ConsoleMessage) => { if (m.type() === "error") consoleErrors.push(m.text().slice(0, 300)); });
        page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message.slice(0, 300)}`));
        page.on("response", (r) => {
          if (r.url().startsWith(API) && r.status() >= 400) failedRequests.push(`${r.status()} ${r.request().method()} ${r.url().replace(API, "")}`);
        });
        page.on("requestfailed", (r) => { if (r.url().startsWith(API)) failedRequests.push(`FAILED ${r.url().replace(API, "")}: ${r.failure()?.errorText}`); });

        const t0 = Date.now();
        await page.goto(route, { waitUntil: "domcontentloaded" });
        await page.waitForLoadState("networkidle", { timeout: 120_000 }).catch(() => undefined);
        await page.waitForTimeout(800);
        const ms = Date.now() - t0;

        const a = await audit(page);
        const broken = a.text.split("\n").filter((l) => BROKEN_TEXT.test(l)).map((l) => l.trim().slice(0, 160)).slice(0, 10);
        const f: Findings = {
          org, route, viewport: info.project.name, ms,
          consoleErrors, failedRequests, brokenText: broken,
          horizontalOverflow: a.overflow, widestElement: a.widestElement, headerOverlaps: a.headerOverlaps, clipped: a.clipped, unlabelled: a.unlabelled, emptyStates: a.emptyStates,
        };
        const slug = route === "/" ? "home" : route.slice(1).replace(/\//g, "__");
        const dir = path.join(OUT, "crawl", info.project.name, org);
        fs.mkdirSync(dir, { recursive: true });
        fs.writeFileSync(path.join(dir, `${slug}.json`), JSON.stringify(f, null, 2));
        await page.screenshot({ path: path.join(dir, `${slug}.png`), fullPage: true });

        expect.soft(consoleErrors, "console errors").toEqual([]);
        expect.soft(failedRequests, "failed API calls").toEqual([]);
        expect.soft(broken, "unformatted values on screen").toEqual([]);
        expect.soft(a.overflow, "sideways scroll (px)").toBeLessThanOrEqual(1);
        expect.soft(a.headerOverlaps, "header controls overlapping").toEqual([]);
      });
    }
  });
}
