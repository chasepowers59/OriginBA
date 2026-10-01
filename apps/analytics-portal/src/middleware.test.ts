import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { config, middleware } from "./middleware";

/**
 * The matcher decides what auth even applies to, and getting it wrong is invisible: a file routed
 * through the auth redirect answers an image request with the login page's HTML, so the logo just
 * is not there and nothing in the console says why. That shipped once, because the matcher listed
 * the public files by name and only brand-icon.svg had ever been added to the list.
 */
const matches = (path: string) =>
  config.matcher.some((m) => new RegExp(`^${m}$`).test(path));

describe("middleware matcher", () => {
  it("never routes a file in public/ through auth", () => {
    // Every file the app actually ships, plus shapes a future one might take.
    for (const file of [
      "/origin-logo.png",
      "/origin-logo-white.png",
      "/origin-mark.png",
      "/brand-icon.svg",
      "/favicon.ico",
      "/robots.txt",
      "/fonts/whatever.woff2",
    ]) {
      expect(matches(file), `${file} must be served directly, not redirected to /login`).toBe(false);
    }
  });

  it("leaves Next's own assets alone", () => {
    expect(matches("/_next/static/chunks/main.js")).toBe(false);
    expect(matches("/_next/image")).toBe(false);
  });

  it("still applies to every app route", () => {
    for (const route of [
      "/",
      "/login",
      "/build",
      "/explore/rpt_bill_segment",
      "/workstream/billing",
      "/settings",
      "/ellensburg",           // a tenant landing
    ]) {
      expect(matches(route), `${route} must still go through the middleware`).toBe(true);
    }
  });
});

describe("app routes are not tenant slugs", () => {
  // A top-level route missing from APP_ROUTES reads as a tenant landing: a signed-in person is
  // sent home and never reaches it. Invisible locally, where sign-in is usually off.
  const signedIn = (path: string) =>
    middleware(new NextRequest(`http://localhost:3000${path}`, { headers: { cookie: "portal_session=1" } }));

  it("opens /letters for a signed-in person instead of redirecting", () => {
    const res = signedIn("/letters");
    expect(res.headers.get("location")).toBeNull();
    expect(res.headers.get("x-middleware-next")).toBe("1");
  });

  it("opens every top-level page in src/app for a signed-in person", () => {
    // /forecasts shipped without its entry (2026-10-01); every page folder is checked, not a list
    const app = path.join(__dirname, "app");
    const pages = fs.readdirSync(app, { withFileTypes: true })
      .filter((d) => d.isDirectory() && !d.name.startsWith("[") && !d.name.startsWith("(") && d.name !== "api"
        && fs.existsSync(path.join(app, d.name, "page.tsx")))
      .map((d) => `/${d.name}`);
    expect(pages).toContain("/forecasts");
    for (const page of pages) {
      expect(signedIn(page).headers.get("location"), `${page} is missing from APP_ROUTES`).toBeNull();
    }
  });

  it("still treats an unknown single segment as a tenant landing", () => {
    expect(signedIn("/ellensburg").headers.get("location")).toMatch(/\/$/);
  });
});
