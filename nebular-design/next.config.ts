import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Hides the floating Next.js dev badge in the corner. Development only — it was
  // never part of a production build. Build and runtime errors still surface.
  devIndicators: false,
  // Nothing uses next/image today — every photo and render is a plain <img>,
  // because they are presigned URLs that expire and the optimiser's cache would
  // outlive the signature. Kept current anyway so that adding one later fails on
  // its own merits rather than on a stale allowlist.
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "*.r2.cloudflarestorage.com" },
      { protocol: "https", hostname: "*.s3.*.amazonaws.com" },
      { protocol: "https", hostname: "*.fly.dev" },
    ],
  },
};

export default nextConfig;
