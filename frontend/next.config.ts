import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Backend (FastAPI) base URL — local-first default.
  env: {
    ASTERION_API_URL: process.env.ASTERION_API_URL ?? "http://localhost:8000",
  },
};

export default nextConfig;
