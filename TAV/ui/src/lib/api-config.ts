/**
 * Centralized API Configuration
 * Single source of truth for API base URL
 * 
 * Port Configuration:
 * - NEXT_PUBLIC_BACKEND_PORT: Backend port (default: 5000)
 * - NEXT_PUBLIC_API_URL: Full override (takes precedence if set)
 * 
 * Auto-detects backend URL based on current environment:
 * - If accessed via localhost → backend at localhost:<BACKEND_PORT>
 * - If accessed via LAN IP → backend at same IP:<BACKEND_PORT>
 */

// Get backend port from environment or default
const BACKEND_PORT = process.env.NEXT_PUBLIC_BACKEND_PORT || '5000';

/**
 * Dynamic API URL detection (works for both local and LAN)
 * Always computes fresh on the client to ensure correct URL after SSR hydration
 */
export function getApiBaseUrl(): string {
  // Server-side rendering: use environment variable or default
  if (typeof window === 'undefined') {
    return process.env.NEXT_PUBLIC_API_URL || `http://localhost:${BACKEND_PORT}`;
  }
  
  // If full API URL is explicitly set via env var, use it
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  
  // Client-side: detect from current hostname (always fresh, no caching)
  const hostname = window.location.hostname;
  const protocol = window.location.protocol;
  
  
  // If accessed via localhost/127.0.0.1, use localhost:<port>
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    const url = `${protocol}//localhost:${BACKEND_PORT}`;
    return url;
  }
  
  // If accessed via IP address, use same IP:<port>
  const url = `${protocol}//${hostname}:${BACKEND_PORT}`;
  return url;
}

// DEPRECATED: This constant is evaluated at module load time during SSR
// and will be stale on the client. Use getApiBaseUrl() instead.
// Keeping for backward compatibility but all new code should use the function.
export const API_BASE_URL = typeof window !== 'undefined' 
  ? getApiBaseUrl() 
  : (process.env.NEXT_PUBLIC_API_URL || `http://localhost:${BACKEND_PORT}`);

/**
 * Get the full API URL for a given endpoint
 * @param endpoint - The API endpoint (e.g., '/api/v1/workflows')
 * @returns The full URL
 */
export function getApiUrl(endpoint: string): string {
  // Remove leading slash if present to avoid double slashes
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${getApiBaseUrl()}${cleanEndpoint}`;
}

