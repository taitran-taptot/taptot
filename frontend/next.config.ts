import type { NextConfig } from "next";

const API_PROXY_TARGET =
  process.env.API_PROXY_TARGET?.replace(/\/$/, "") || "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  typescript: { ignoreBuildErrors: true },
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  // Challenge 100-day generate can exceed the default ~30s rewrite proxy timeout
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
        // Same turbopack issue: `/tai-khoan/lich/[id]` 404s, so serve the static edit page.
        {
          source: "/tai-khoan/lich/:id",
          destination: "/tai-khoan/lich?id=:id",
        },
        // `/batdau/[ma]` is missing from the turbopack route manifest → 404.
        {
          source: "/batdau/:ma",
          destination: "/batdau?code=:ma",
        },
        // `/mua-dung-cu/[slug]` 404s in the turbopack route manifest.
        {
          source: "/mua-dung-cu/:slug",
          destination: "/mua-dung-cu?san-pham=:slug",
        },
        // Same turbopack issue: `/lich/[token]` 404s after generate.
        {
          source: "/lich/:token",
          destination: "/lich?token=:token",
        },
        // Nested `/don-hang/thanh-cong` and `/don-hang/thanh-toan` are missing from the route manifest.
        {
          source: "/don-hang/thanh-cong",
          destination: "/don-hang?ket-qua=thanh-cong",
        },
        {
          source: "/don-hang/thanh-toan",
          destination: "/don-hang?ket-qua=thanh-toan",
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
      { source: "/spec-lich", destination: "/tai-khoan/quan-tri?tab=bai-tap", permanent: false },
      { source: "/hlv", destination: "/tai-khoan", permanent: false },
      { source: "/hlv/hoc-vien", destination: "/tai-khoan", permanent: false },
      { source: "/hlv/profile", destination: "/tai-khoan", permanent: false },
      { source: "/hlv/p/:token", destination: "/lien-he", permanent: false },
      { source: "/kho-bai-tap", destination: "/bai-tap", permanent: false },
      { source: "/kho-thuc-pham", destination: "/thuc-an", permanent: false },
      { source: "/dung-cu", destination: "/mua-dung-cu", permanent: false },
      { source: "/sukien/giam-gia", destination: "/sukien/chongday-giamgia", permanent: true },
      { source: "/sukien/plank", destination: "/sukien/plank-giamgia", permanent: true },
      { source: "/mua-dung-cu/dumbbell", destination: "/mua-dung-cu/ta-don", permanent: true },
      { source: "/mua-dung-cu/resistance-band", destination: "/mua-dung-cu/day-khang-luc", permanent: true },
      { source: "/mua-dung-cu/bar-and-rings", destination: "/mua-dung-cu/xa-don-va-vong-treo", permanent: true },
      { source: "/mua-dung-cu/pull-up-bar", destination: "/mua-dung-cu/xa-don-va-vong-treo", permanent: true },
      { source: "/mua-dung-cu/gymnastic-rings", destination: "/mua-dung-cu/xa-don-va-vong-treo", permanent: true },
      { source: "/tai-khoan/dung-cu", destination: "/mua-dung-cu", permanent: false },
      { source: "/qua-tang", destination: "/batdau?nhap-ma=1", permanent: false },
      { source: "/mon-truyen-thong", destination: "/thuc-an", permanent: false },
      { source: "/mon-truyen-thong/:path*", destination: "/thuc-an", permanent: false },
      {
        source: "/thuc-an",
        has: [{ type: "query", key: "tab", value: "dishes" }],
        destination: "/thuc-an",
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
