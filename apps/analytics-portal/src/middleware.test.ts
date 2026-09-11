import { describe, expect, it } from "vitest";
import { config } from "./middleware";

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
