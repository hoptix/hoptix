/**
 * Authenticated API client with automatic token attachment and refresh
 */

import { refreshSession } from './auth-api'
import { getRefreshToken, setRefreshToken, removeRefreshToken } from './token-storage'

const API_BASE_URL = process.env.NEXT_PUBLIC_FLASK_API_URL || 'http://localhost:8081'

// Store access token in memory (module-level variable)
let accessToken: string | null = null

// Track ongoing refresh request to prevent multiple simultaneous refreshes
let refreshPromise: Promise<string> | null = null

/**
 * Set the access token (called by AuthContext)
 */
export function setAccessToken(token: string | null): void {
  accessToken = token
}

/**
 * Get the current access token
 */
export function getAccessToken(): string | null {
  return accessToken
}

/**
 * Attempt to refresh the access token
 */
async function attemptTokenRefresh(): Promise<string> {
  // If already refreshing, return the existing promise
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = (async () => {
    try {
      const refreshToken = getRefreshToken()

      if (!refreshToken) {
        throw new Error('No refresh token available')
      }

      const response = await refreshSession(refreshToken)

      // Update tokens
      accessToken = response.access_token
      setRefreshToken(response.refresh_token)

      return response.access_token
    } catch (error) {
      // Refresh failed - clear everything and throw
      accessToken = null
      removeRefreshToken()
      throw error
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}

/**
 * Make an authenticated API request
 */
async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  // Prepare the request
  const fullUrl = url.startsWith('http') ? url : `${API_BASE_URL}${url}`

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  // Attach access token if available
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`
  }

  const requestOptions: RequestInit = {
    ...options,
    headers,
  }

  try {
    const response = await fetch(fullUrl, requestOptions)

    // Handle 401 - try to refresh token and retry
    if (response.status === 401 && getRefreshToken()) {
      try {
        // Attempt to refresh the token
        const newAccessToken = await attemptTokenRefresh()

        // Retry the original request with new token
        headers['Authorization'] = `Bearer ${newAccessToken}`
        const retryResponse = await fetch(fullUrl, {
          ...requestOptions,
          headers,
        })

        if (!retryResponse.ok && retryResponse.status !== 401) {
          throw new Error(`HTTP ${retryResponse.status}: ${retryResponse.statusText}`)
        }

        // If still 401 after refresh, user needs to log in again
        if (retryResponse.status === 401) {
          throw new Error('Authentication failed - please log in again')
        }

        return await retryResponse.json()
      } catch (refreshError) {
        // Refresh failed - trigger logout
        accessToken = null
        removeRefreshToken()

        // Redirect to login
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }

        throw new Error('Session expired - please log in again')
      }
    }

    // Handle other error status codes
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`)
    }

    // Return response data
    return await response.json()
  } catch (error) {
    // Re-throw the error to be handled by the caller
    throw error
  }
}

/**
 * API client with convenience methods
 */
export const apiClient = {
  get: <T>(url: string, options?: RequestInit) =>
    request<T>(url, { ...options, method: 'GET' }),

  post: <T>(url: string, data?: any, options?: RequestInit) =>
    request<T>(url, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T>(url: string, data?: any, options?: RequestInit) =>
    request<T>(url, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T>(url: string, options?: RequestInit) =>
    request<T>(url, { ...options, method: 'DELETE' }),

  patch: <T>(url: string, data?: any, options?: RequestInit) =>
    request<T>(url, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    }),
}
