/**
 * Auth-related TypeScript types and interfaces
 */

export interface User {
  id: string
  email: string
}

export interface AuthTokens {
  accessToken: string
  refreshToken: string
}

export interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user: User
}

export interface RefreshResponse {
  access_token: string
  refresh_token: string
  user: User
}

export interface AuthError {
  message: string
  code?: string
}
