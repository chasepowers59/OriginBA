import type { NextConfig } from "next";
import { frameHeaders } from "./src/lib/publicPaths";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // don't advertise the framework and version on every response
  poweredByHeader: false,
  // Clickjacking: no page may be framed, except an embed by the sites in EMBED_ALLOWED_ORIGINS;
  // and the production security headers on every page (src/lib/publicPaths.ts).
  async headers() {
    return frameHeaders(process.env.EMBED_ALLOWED_ORIGINS);
  },
};

export default nextConfig;
