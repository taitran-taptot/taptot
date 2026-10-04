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
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' 'wasm-unsafe-eval'",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https:",
              "font-src 'self' data:",
              // Pose landmarker WASM (jsDelivr) + .task model (Google Storage)
              "connect-src 'self' https://cdn.jsdelivr.net https://storage.googleapis.com",
              "worker-src 'self' blob: https://cdn.jsdelivr.net",
              "child-src 'self' blob: https://cdn.jsdelivr.net",
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
        // Keep browser URL `/kien-thuc/:slug`; serve index with `bai` (no [slug] page — Next 16 turbopack).
        {
          source: "/kien-thuc/:slug",
          destination: "/kien-thuc?bai=:slug",
        },
      ],
    };
  },
  async redirects() {
    return [
      { source: "/ve-chung-toi", destination: "/ve-taptot", permanent: true },
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
      { source: "/qua-tang", destination: "/batdau?nhap-ma=1", permanent: false },
      {
        source: "/thuc-an",
        has: [{ type: "query", key: "tab", value: "dishes" }],
        destination: "/mon-truyen-thong",
        permanent: false,
      },
      // Dynamic `/cach-nau/[slug]` is not registering in Next 16 turbopack manifest → 404.
      // Keep stable query URLs; rewrite path style for bookmarks / old links.
      {
        source: "/cach-nau/:slug",
        destination: "/cach-nau?mon=:slug",
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
