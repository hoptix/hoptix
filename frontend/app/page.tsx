"use client"

/**
 * Root Page - Authentication-aware landing page
 * Redirects users based on authentication status:
 * - Authenticated users → /dashboard
 * - Unauthenticated users → /login
 */

import { useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/authContext"

export default function RootPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const hasRedirected = useRef(false)

  useEffect(() => {
    // Wait for auth check to complete
    if (isLoading) return

    // Prevent duplicate redirects using ref
    if (hasRedirected.current) return

    // Mark as redirected
    hasRedirected.current = true

    // Redirect based on authentication status
    if (isAuthenticated) {
      // Authenticated users go to dashboard
      router.replace("/dashboard")
    } else {
      // Unauthenticated users go to login
      router.replace("/login")
    }
  }, [isAuthenticated, isLoading, router])

  // Show loading spinner while checking auth
  return (
    <div className="flex h-screen items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
        <p className="text-sm text-muted-foreground">
          {isLoading ? "Loading..." : "Redirecting..."}
        </p>
      </div>
    </div>
  )
}
