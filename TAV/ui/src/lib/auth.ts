/**
 * Authentication Token Management
 * 
 * Handles JWT token storage and retrieval for SSO authentication
 */

const TOKEN_KEY = 'tav_auth_token';

/**
 * Get the authentication token from localStorage
 */
export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

/**
 * Set the authentication token in localStorage
 */
export function setAuthToken(token: string): void {
  if (typeof window === 'undefined') return;
  localStorage.setItem(TOKEN_KEY, token);
}

/**
 * Remove the authentication token from localStorage
 */
export function clearAuthToken(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(TOKEN_KEY);
}

/**
 * Check if user is authenticated (has a valid token)
 */
export function isAuthenticated(): boolean {
  return getAuthToken() !== null;
}

/**
 * Extract token from URL query parameter and store it
 * Returns true if token was found and stored
 */
export function extractAndStoreTokenFromUrl(): boolean {
  if (typeof window === 'undefined') return false;
  
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get('token');
  
  if (token) {
    console.log('🔑 Token found in URL:', token.substring(0, 50) + '...');
    setAuthToken(token);
    
    // Verify it was stored
    const stored = getAuthToken();
    console.log('✅ Token stored successfully:', stored?.substring(0, 50) + '...');
    
    // Remove token from URL (clean up)
    urlParams.delete('token');
    const newSearch = urlParams.toString();
    const newUrl = `${window.location.pathname}${newSearch ? '?' + newSearch : ''}`;
    window.history.replaceState({}, '', newUrl);
    
    console.log('✅ Authentication token extracted and stored from URL');
    return true;
  } else {
    console.log('ℹ️  No token in URL');
    const existingToken = getAuthToken();
    if (existingToken) {
      console.log('✅ Using existing token from localStorage:', existingToken.substring(0, 50) + '...');
    } else {
      console.log('⚠️  No token found anywhere (URL or localStorage)');
    }
  }
  
  return false;
}

/**
 * Get authorization headers for API requests
 */
export function getAuthHeaders(): Record<string, string> {
  const token = getAuthToken();
  if (token) {
    console.log('📤 Sending Authorization header with token:', token.substring(0, 50) + '...');
    return {
      'Authorization': `Bearer ${token}`,
    };
  }
  console.log('⚠️  No token available - API call without Authorization header');
  return {};
}

