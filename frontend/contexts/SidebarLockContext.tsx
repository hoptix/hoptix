"use client"

import React, { createContext, useContext, useState, useCallback } from "react"

interface SidebarLockContextType {
  isLocked: boolean
  lockSidebar: () => void
  unlockSidebar: () => void
}

const SidebarLockContext = createContext<SidebarLockContextType | undefined>(undefined)

export function SidebarLockProvider({ children }: { children: React.ReactNode }) {
  const [isLocked, setIsLocked] = useState(false)

  const lockSidebar = useCallback(() => {
    setIsLocked(true)
  }, [])

  const unlockSidebar = useCallback(() => {
    setIsLocked(false)
  }, [])

  return (
    <SidebarLockContext.Provider value={{ isLocked, lockSidebar, unlockSidebar }}>
      {children}
    </SidebarLockContext.Provider>
  )
}

export function useSidebarLock() {
  const context = useContext(SidebarLockContext)
  if (context === undefined) {
    throw new Error("useSidebarLock must be used within a SidebarLockProvider")
  }
  return context
}
