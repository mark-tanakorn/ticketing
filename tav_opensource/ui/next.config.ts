import type { NextConfig } from "next";

// Get ports from environment with defaults
const BACKEND_PORT = process.env.NEXT_PUBLIC_BACKEND_PORT || '5000';

const nextConfig: NextConfig = {
  output: 'standalone',
  // Environment variables for the frontend
  // Note: NEXT_PUBLIC_API_URL is intentionally NOT set here with a fallback
  // so that the client-side getApiBaseUrl() can dynamically detect based on
  // window.location.hostname (for LAN access support)
  env: {
    NEXT_PUBLIC_BACKEND_PORT: BACKEND_PORT,
    // Only pass through explicit API URL if set, otherwise let client detect dynamically
    ...(process.env.NEXT_PUBLIC_API_URL ? { NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL } : {}),
  },
  webpack: (config) => {
    // Ignore Node.js canvas module that pdfjs-dist tries to use
    config.resolve.alias.canvas = false;
    return config;
  },
};

export default nextConfig;
  