"use client"

/**
 * Root Page - Authentication-aware landing page
 * Redirects users based on authentication status:
 * - Authenticated users → /dashboard
 * - Unauthenticated users → /login
 */

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/AuthContext"

export default function RootPage() {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const [isRedirecting, setIsRedirecting] = useState(false)

  useEffect(() => {
    // Wait for auth check to complete
    if (isLoading) return

    // Prevent duplicate redirects
    if (isRedirecting) return

    // Redirect based on authentication status
    setIsRedirecting(true)
    if (isAuthenticated) {
      // Authenticated users go to dashboard
      router.replace("/dashboard")
    } else {
      // Unauthenticated users go to login
      router.replace("/login")
    }
  }, [isAuthenticated, isLoading, isRedirecting, router])

  // Show loading spinner while checking auth or redirecting
  if (isLoading || isRedirecting) {
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

  // Don't render any content - we're always redirecting
  return null
}
