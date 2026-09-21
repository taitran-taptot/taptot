import type { NextConfig } from "next";

const API_PROXY_TARGET =
  process.env.API_PROXY_TARGET?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Challenge 100-day OpenAI gen often exceeds the default ~30s rewrite proxy timeout
  // ("socket hang up" → browser sees Internal Server Error).
  experimental: {
    proxyTimeout: 180_000,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https:",
              "font-src 'self' data:",
              "connect-src 'self'",
              "media-src 'self' blob:",
              "frame-src https://www.youtube-nocookie.com https://www.youtube.com",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
              "frame-ancestors 'none'",
            ].join("; "),
          },
        ],
      },
    ];
  },
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: "/api/v1/:path*",
          destination: `${API_PROXY_TARGET}/api/v1/:path*`,
        },
        {
          source: "/media/:path*",
          destination: `${API_PROXY_TARGET}/media/:path*`,
        },
      ],
    };
  },
  async redirects() {
    return [
      { source: "/reset-password", destination: "/dat-lai-mat-khau", permanent: false },
      { source: "/verify-email", destination: "/xac-thuc-email", permanent: false },
      { source: "/bat-dau", destination: "/batdau", permanent: false },
      { source: "/tao-lich-tap", destination: "/batdau", permanent: false },
      { source: "/tao-lich-tap/taptot", destination: "/batdau", permanent: false },
      { source: "/tao-lich-tap/tfit", destination: "/batdau", permanent: false },
      { source: "/tai-khoan/tao-lich-tap", destination: "/tai-khoan/batdau", permanent: false },
      { source: "/tai-khoan/tao-lich-tap/taptot", destination: "/tai-khoan/batdau", permanent: false },
      { source: "/tai-khoan/tao-lich-tap/tfit", destination: "/tai-khoan/batdau", permanent: false },
      { source: "/hlv", destination: "/tai-khoan", permanent: false },
      { source: "/hlv/hoc-vien", destination: "/tai-khoan", permanent: false },
      { source: "/hlv/profile", destination: "/tai-khoan", permanent: false },
      { source: "/hlv/p/:token", destination: "/lien-he", permanent: false },
      { source: "/kho-bai-tap", destination: "/bai-tap", permanent: false },
      { source: "/kho-thuc-pham", destination: "/thuc-an", permanent: false },
      { source: "/dung-cu", destination: "/mua-dung-cu", permanent: false },
      { source: "/tai-khoan/dung-cu", destination: "/mua-dung-cu", permanent: false },
      {
        source: "/thuc-an",
        has: [{ type: "query", key: "tab", value: "dishes" }],
        destination: "/mon-truyen-thong",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
