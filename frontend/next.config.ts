import type { NextConfig } from "next";

const isProduction = process.env.NODE_ENV === "production";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: [
      "microphone=(self)",
      "camera=()",
      "geolocation=()",
      "clipboard-write=(self)",
      "autoplay=(self)",
      "accelerometer=()",
      "gyroscope=()",
      "magnetometer=()",
      "payment=()",
      "usb=()",
      "xr-spatial-tracking=()"
    ].join(", ")
  }
];

const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  env: {
    NEXT_PUBLIC_BUILD_NUMBER: process.env.NEXT_PUBLIC_BUILD_NUMBER || process.env.GITHUB_RUN_NUMBER || ""
  },
  experimental: {
    proxyTimeout: 300_000
  },
  turbopack: {
    root: __dirname
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          ...securityHeaders,
          ...(isProduction ? [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" }] : [])
        ]
      }
    ];
  }
};

export default nextConfig;
