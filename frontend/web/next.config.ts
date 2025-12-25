import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: __dirname,
  },
  webpack: (config, { dev }) => {
    if (dev) {
      // Avoid filesystem cache flakiness (ENOENT for .pack.gz / manifests) in dev.
      // Disable webpack cache entirely to prevent file-system races when restarting dev server.
      config.cache = false;
    }
    return config;
  },
};

export default nextConfig;
