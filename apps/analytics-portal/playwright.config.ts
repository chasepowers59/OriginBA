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
    colorScheme: "light",
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 900 } } },
    { name: "phone", use: { viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true } },
    // The smallest phone in use; the header overlapped the logo here and nowhere wider.
    { name: "small-phone", use: { viewport: { width: 320, height: 640 }, isMobile: true, hasTouch: true } },
  ],
});
