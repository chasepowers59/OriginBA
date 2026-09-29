import { defineConfig } from "@playwright/test";

// The crawl drives the installed Google Chrome against the dev servers already running
// (portal-ui on 3001, portal-api on 8010); it never downloads a browser or starts a
// server. Screenshots and reports go under e2e/.out, which is gitignored: pages for a
// client org render that client's real customer names.
export default defineConfig({
  testDir: "./e2e",
  outputDir: "./e2e/.out/results",
  snapshotPathTemplate: "e2e/.out/baseline/{projectName}/{arg}{ext}",
  timeout: 180_000,
  workers: 2,
  reporter: [["list"]],
  use: {
    baseURL: process.env.PORTAL_URL ?? "http://localhost:3001",
    channel: "chrome",
    headless: true,
    colorScheme: (process.env.COLOR_SCHEME as "light" | "dark" | undefined) ?? "light",
  },
  // Desktop web only (Chase, 2026-09-29): no app store, no phone target.
  projects: [{ name: "desktop", use: { viewport: { width: 1440, height: 900 } } }],
});
