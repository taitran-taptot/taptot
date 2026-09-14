import type { NextConfig } from "next";

const API_PROXY_TARGET =
  process.env.API_PROXY_TARGET?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  // Challenge 100-day OpenAI gen often exceeds the default ~30s rewrite proxy timeout
  // ("socket hang up" → browser sees Internal Server Error).
  experimental: {
    proxyTimeout: 180_000,
  },
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/api/v1/:path*",
          destination: `${API_PROXY_TARGET}/api/v1/:path*`,
        },
      ],
    };
  },
  async redirects() {
    return [
      { source: "/reset-password", destination: "/dat-lai-mat-khau", permanent: false },
      { source: "/verify-email", destination: "/xac-thuc-email", permanent: false },
      { source: "/tao-lich-tap", destination: "/bat-dau", permanent: false },
      { source: "/tai-khoan/tao-lich-tap", destination: "/bat-dau", permanent: false },
      { source: "/tao-lich-tap/tfit", destination: "/tao-lich-tap/taptot", permanent: false },
      { source: "/tai-khoan/tao-lich-tap/tfit", destination: "/tai-khoan/tao-lich-tap/taptot", permanent: false },
    ];
  },
};

export default nextConfig;
