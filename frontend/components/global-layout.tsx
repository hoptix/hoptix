"use client"

import { usePathname } from "next/navigation"
import { AppSidebar } from "@/components/app-sidebar"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

interface GlobalLayoutProps {
  children: React.ReactNode
}

/**
 * Global layout component that wraps all pages with the sidebar
 * Excludes sidebar from certain routes like /login
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
    <SidebarProvider>
      <AppSidebar variant="sidebar" />
      <SidebarInset>
        <div className="flex flex-1 flex-col">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  )
}
