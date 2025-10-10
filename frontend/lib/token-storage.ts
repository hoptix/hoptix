/**
 * Token storage utilities for managing refresh tokens in sessionStorage
 * and decoding JWTs for expiry information
 */

const REFRESH_TOKEN_KEY = 'hoptix_refresh_token'

/**
 * Save refresh token to sessionStorage
 */
export function setRefreshToken(token: string): void {
  if (typeof window !== 'undefined') {
    sessionStorage.setItem(REFRESH_TOKEN_KEY, token)
  }
}

/**
 * Get refresh token from sessionStorage
 */
export function getRefreshToken(): string | null {
  if (typeof window !== 'undefined') {
    return sessionStorage.getItem(REFRESH_TOKEN_KEY)
  }
  return null
}

/**
 * Remove refresh token from sessionStorage
 */
export function removeRefreshToken(): void {
  if (typeof window !== 'undefined') {
    sessionStorage.removeItem(REFRESH_TOKEN_KEY)
  }
}

/**
 * Decode JWT token to get payload
 * Note: This does NOT verify the signature - only decodes the payload
 */
export function decodeToken(token: string): {
  sub?: string
  email?: string
  exp?: number
  iat?: number
  [key: string]: any
} | null {
  try {
    const parts = token.split('.')
    if (parts.length !== 3) {
      return null
    }

    // Decode the payload (second part)
    const payload = parts[1]
    const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'))
    return JSON.parse(decoded)
  } catch (error) {
    console.error('Error decoding token:', error)
    return null
  }
}

/**
 * Check if token is expired
 */
export function isTokenExpired(token: string): boolean {
  const decoded = decodeToken(token)
  if (!decoded || !decoded.exp) {
    return true
  }

  // exp is in seconds, Date.now() is in milliseconds
  const expiryTime = decoded.exp * 1000
  return Date.now() >= expiryTime
}

/**
 * Get time until token expires (in milliseconds)
 * Returns 0 if token is already expired
 */
export function getTimeUntilExpiry(token: string): number {
  const decoded = decodeToken(token)
  if (!decoded || !decoded.exp) {
    return 0
  }

  const expiryTime = decoded.exp * 1000
  const timeRemaining = expiryTime - Date.now()
  return Math.max(0, timeRemaining)
}
