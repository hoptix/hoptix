"use client"

/**
 * Auth Context - Central authentication state management
 */

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { useRouter } from 'next/navigation'
import type { User, AuthState, LoginCredentials } from '@/types/auth'
import { loginUser, refreshSession, AuthApiError } from '@/lib/auth-api'
import {
  setRefreshToken,
  getRefreshToken,
  removeRefreshToken,
  getTimeUntilExpiry,
} from '@/lib/token-storage'
import { setAccessToken as setGlobalAccessToken } from '@/lib/api-client'

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
  refreshToken: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Refresh token 5 minutes before expiry
const REFRESH_BUFFER_MS = 5 * 60 * 1000

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  // Use ref to avoid recreating setTimeout on every render
  const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  /**
   * Schedule the next token refresh
   */
  const scheduleTokenRefresh = useCallback((accessToken: string) => {
    // Clear any existing timeout
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current)
    }

    // Calculate when to refresh
    const timeUntilExpiry = getTimeUntilExpiry(accessToken)
    const refreshTime = Math.max(0, timeUntilExpiry - REFRESH_BUFFER_MS)

    // Schedule refresh
    refreshTimeoutRef.current = setTimeout(async () => {
      try {
        await refreshTokenInternal()
      } catch (error) {
        console.error('Auto-refresh failed:', error)
        logout()
      }
    }, refreshTime)
  }, [])

  /**
   * Internal refresh function
   */
  const refreshTokenInternal = useCallback(async () => {
    const storedRefreshToken = getRefreshToken()

    if (!storedRefreshToken) {
      throw new Error('No refresh token available')
    }

    try {
      const response = await refreshSession(storedRefreshToken)

      // Update state
      setUser(response.user)
      setIsAuthenticated(true)

      // Update global access token
      setGlobalAccessToken(response.access_token)

      // Store new refresh token
      setRefreshToken(response.refresh_token)

      // Schedule next refresh
      scheduleTokenRefresh(response.access_token)

      return response.access_token
    } catch (error) {
      // Refresh failed
      setUser(null)
      setIsAuthenticated(false)
      setGlobalAccessToken(null)
      removeRefreshToken()
      throw error
    }
  }, [scheduleTokenRefresh])

  /**
   * Login function
   */
  const login = useCallback(async (credentials: LoginCredentials) => {
    try {
      const response = await loginUser(credentials)

      // Update state
      setUser(response.user)
      setIsAuthenticated(true)

      // Update global access token
      setGlobalAccessToken(response.access_token)

      // Store refresh token
      setRefreshToken(response.refresh_token)

      // Schedule token refresh
      scheduleTokenRefresh(response.access_token)

      // Navigate to dashboard
      router.push('/dashboard')
    } catch (error) {
      // Clear state on login failure
      setUser(null)
      setIsAuthenticated(false)
      setGlobalAccessToken(null)
      removeRefreshToken()

      // Re-throw for UI to handle
      throw error
    }
  }, [router, scheduleTokenRefresh])

  /**
   * Logout function
   */
  const logout = useCallback(() => {
    // Clear timeout
    if (refreshTimeoutRef.current) {
      clearTimeout(refreshTimeoutRef.current)
    }

    // Clear state
    setUser(null)
    setIsAuthenticated(false)

    // Clear tokens
    setGlobalAccessToken(null)
    removeRefreshToken()

    // Redirect to login
    router.push('/login')
  }, [router])

  /**
   * Exposed refresh function
   */
  const refreshToken = useCallback(async () => {
    await refreshTokenInternal()
  }, [refreshTokenInternal])

  /**
   * Initialize auth state on mount
   */
  useEffect(() => {
    const initializeAuth = async () => {
      const storedRefreshToken = getRefreshToken()

      if (storedRefreshToken) {
        try {
          // Try to refresh to get a new access token
          await refreshTokenInternal()
        } catch (error) {
          console.error('Failed to restore session:', error)
          // Session restoration failed - user needs to log in again
          setUser(null)
          setIsAuthenticated(false)
          setGlobalAccessToken(null)
          removeRefreshToken()
        }
      }

      setIsLoading(false)
    }

    initializeAuth()
  }, [refreshTokenInternal])

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (refreshTimeoutRef.current) {
        clearTimeout(refreshTimeoutRef.current)
      }
    }
  }, [])

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    login,
    logout,
    refreshToken,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

/**
 * Hook to use auth context
 */
export function useAuth() {
  const context = useContext(AuthContext)

  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }

  return context
}
