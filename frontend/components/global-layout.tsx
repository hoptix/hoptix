"use client"

import { useState, useRef, useCallback } from "react"
import { usePathname } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { SidebarLockProvider, useSidebarLock } from "@/contexts/SidebarLockContext"

interface GlobalLayoutProps {
  children: React.ReactNode
}

/**
 * Internal component that handles sidebar hover behavior
 * Separated to use the SidebarLockContext
 */
function SidebarContent({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  const { isLocked } = useSidebarLock()
  const collapseTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  const handleMouseEnter = useCallback(() => {
    // Clear any pending collapse timeout
    if (collapseTimeoutRef.current) {
      clearTimeout(collapseTimeoutRef.current)
      collapseTimeoutRef.current = null
    }
    setOpen(true)
  }, [])

  const handleMouseLeave = useCallback(() => {
    // Don't collapse if a dropdown is open
    if (isLocked) {
      return
    }

    // Add a small delay before collapsing to prevent accidental closures
    collapseTimeoutRef.current = setTimeout(() => {
      setOpen(false)
    }, 150)
  }, [isLocked])

  return (
    <SidebarProvider open={open} onOpenChange={setOpen}>
      <div
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
        <AppSidebar variant="sidebar" />
      </div>
      <SidebarInset className="overflow-x-hidden">
        {children}
      </SidebarInset>
    </SidebarProvider>
  )
}

/**
 * Global layout component that wraps all pages with the sidebar
 * Excludes sidebar from certain routes like /login
 * Sidebar expands on hover and collapses when mouse leaves
 * Prevents collapse when dropdown menus are open
 */
export function GlobalLayout({ children }: GlobalLayoutProps) {
  const pathname = usePathname()

  // Routes that should not have the sidebar
  const excludedRoutes = ['/login']
  const showSidebar = !excludedRoutes.includes(pathname)

  if (!showSidebar) {
    return <>{children}</>
  }

  return (
    <SidebarLockProvider>
      <SidebarContent>
        {children}
      </SidebarContent>
    </SidebarLockProvider>
  )
}
