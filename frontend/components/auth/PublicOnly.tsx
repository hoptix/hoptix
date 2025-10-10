"use client"

/**
 * PublicOnly - Route guard for public-only pages (like login)
 * Redirects to dashboard if user is already authenticated
 */

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'

interface PublicOnlyProps {
  children: React.ReactNode
}

export function PublicOnly({ children }: PublicOnlyProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const router = useRouter()
  const [isRedirecting, setIsRedirecting] = useState(false)

  useEffect(() => {
    if (!isLoading && isAuthenticated && !isRedirecting) {
      setIsRedirecting(true)
      // Use replace instead of push to prevent back button navigation to login
      router.replace('/dashboard')
    }
  }, [isAuthenticated, isLoading, isRedirecting, router])

  // Show loading spinner while checking auth or redirecting
  if (isLoading || (isAuthenticated && isRedirecting)) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent"></div>
          <p className="text-sm text-muted-foreground">
            {isLoading ? 'Loading...' : 'Redirecting to dashboard...'}
          </p>
        </div>
      </div>
    )
  }

  // Don't render login page if already authenticated
  if (isAuthenticated) {
    return null
  }

  return <>{children}</>
}
