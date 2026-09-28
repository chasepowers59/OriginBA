import type { NextConfig } from "next";
import { frameHeaders } from "./src/lib/publicPaths";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Clickjacking: no page may be framed, except an embed by the sites in EMBED_ALLOWED_ORIGINS.
  async headers() {
    return frameHeaders(process.env.EMBED_ALLOWED_ORIGINS);
  },
};

export default nextConfig;
