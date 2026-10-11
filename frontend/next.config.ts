import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cureva's frontend is a fully client-rendered SPA talking to the Django API
  // with a JWT; the new server-caching model adds friction for client-only
  // dynamic routes, so it's left off.
  cacheComponents: false,
  turbopack: {
    // Pin the workspace root so a stray package-lock.json in a parent dir
    // doesn't make Next guess the wrong root.
    root: import.meta.dirname,
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
