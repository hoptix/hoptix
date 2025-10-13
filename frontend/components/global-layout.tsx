"use client"

import { useState } from "react"
import { usePathname } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

interface GlobalLayoutProps {
  children: React.ReactNode
}

/**
 * Global layout component that wraps all pages with the sidebar
 * Excludes sidebar from certain routes like /login
 * Sidebar expands on hover and collapses when mouse leaves
 */
export function GlobalLayout({ children }: GlobalLayoutProps) {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  // Routes that should not have the sidebar
  const excludedRoutes = ['/login']
  const showSidebar = !excludedRoutes.includes(pathname)

  if (!showSidebar) {
    return <>{children}</>
  }

  return (
    <SidebarProvider open={open} onOpenChange={setOpen}>
      <div
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
      >
        <AppSidebar variant="sidebar" />
      </div>
      <SidebarInset className="overflow-x-hidden">
        <div className="flex flex-1 flex-col overflow-x-hidden">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
