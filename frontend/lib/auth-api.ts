/**
 * Auth API client for communicating with the auth service
 */

import type {
  LoginCredentials,
  LoginResponse,
  RefreshResponse,
  AuthError,
} from '@/types/auth'

const AUTH_SERVICE_URL = process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || 'http://localhost:5000'

/**
 * Custom error class for auth-related errors
 */
export class AuthApiError extends Error {
  code?: string
  statusCode?: number

  constructor(message: string, code?: string, statusCode?: number) {
    super(message)
    this.name = 'AuthApiError'
    this.code = code
    this.statusCode = statusCode
  }
}

/**
 * Login user with email and password
 */
export async function loginUser(credentials: LoginCredentials): Promise<LoginResponse> {
  try {
    const response = await fetch(`${AUTH_SERVICE_URL}/token?grant_type=password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    })

    const data = await response.json()

    if (!response.ok) {
      throw new AuthApiError(
        data.error || data.error_description || 'Login failed',
        'LOGIN_FAILED',
        response.status
      )
    }

    // Ensure is_admin is attached to user object
    if (data.is_admin !== undefined && data.user) {
      data.user.is_admin = data.is_admin
    }

    return data
  } catch (error) {
    if (error instanceof AuthApiError) {
      throw error
    }

    // Network or other errors
    throw new AuthApiError(
      'Unable to connect to auth service. Please check your connection.',
      'NETWORK_ERROR'
    )
  }
}

/**
 * Refresh session using refresh token
 */
export async function refreshSession(refreshToken: string): Promise<RefreshResponse> {
  try {
    const response = await fetch(`${AUTH_SERVICE_URL}/token?grant_type=refresh_token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })

    const data = await response.json()

    if (!response.ok) {
      throw new AuthApiError(
        data.error || data.error_description || 'Session refresh failed',
        'REFRESH_FAILED',
        response.status
      )
    }

    // Ensure is_admin is attached to user object
    if (data.is_admin !== undefined && data.user) {
      data.user.is_admin = data.is_admin
    }

    return data
  } catch (error) {
    if (error instanceof AuthApiError) {
      throw error
    }

    throw new AuthApiError(
      'Unable to refresh session',
      'NETWORK_ERROR'
    )
  }
}

/**
 * Verify token validity
 */
export async function verifyToken(accessToken: string): Promise<boolean> {
  try {
    const response = await fetch(`${AUTH_SERVICE_URL}/verify`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
      },
    })

    const data = await response.json()
    return response.ok && data.valid === true
  } catch (error) {
    return false
  }
}

/**
 * Logout user - calls auth service to invalidate tokens
 * Note: Tokens are cleared from storage regardless of API response
 */
export async function logoutUser(accessToken: string, refreshToken: string): Promise<void> {
  try {
    // Attempt to logout on the server
    await fetch(`${AUTH_SERVICE_URL}/logout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    })
    // We don't throw on errors - logout should always succeed client-side
  } catch (error) {
    // Silently fail - we'll clear tokens anyway
    console.warn('Logout API call failed, but clearing tokens locally:', error)
  }
}
