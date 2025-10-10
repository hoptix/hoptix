"use client"

/**
 * RequireAuth - Route guard that requires authentication
 * Redirects to login if user is not authenticated
 */

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

interface RequireAuthProps {
  children: React.ReactNode
}

export function RequireAuth({ children }: RequireAuthProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const [isRedirecting, setIsRedirecting] = useState(false)

  useEffect(() => {
    if (!isLoading && !isAuthenticated && !isRedirecting) {
      setIsRedirecting(true)
      // Use replace instead of push to prevent back button navigation to protected route
      router.replace('/login')
    }
  }, [isAuthenticated, isLoading, isRedirecting, router])

  // Show loading spinner while checking auth or redirecting
  if (isLoading || (!isAuthenticated && isRedirecting)) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
          <p className="text-sm text-muted-foreground">
            {isLoading ? 'Loading...' : 'Redirecting to login...'}
          </p>
        </div>
      </div>
    )
  }

  // Don't render protected content if not authenticated
  if (!isAuthenticated) {
    return null
  }

  return <>{children}</>
}
