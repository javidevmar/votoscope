import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Route segment config `dynamic = "force-dynamic"` (R3, R4) is incompatible
  // with Cache Components, so the app uses the standard rendering model.
  // `web/AGENTS.md` is maintained by hand; don't let `next dev` append to it.
  agentRules: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
