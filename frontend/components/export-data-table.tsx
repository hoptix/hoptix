"use client"

import * as React from "react"
import * as XLSX from "xlsx"
import { IconDownload, IconFileSpreadsheet, IconFileText } from "@tabler/icons-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

interface DataTableExportProps {
  data: any[]
  filename?: string
  size?: "default" | "sm" | "lg"
  variant?: "default" | "outline" | "ghost"
}

export function DataTableExport({ 
  data,
  filename = "data-export",
  size = "sm",
  variant = "outline"
}: DataTableExportProps) {
  
  const exportToCSV = () => {
    if (!data || data.length === 0) return
    
    // Get headers from the first data object
    const headers = Object.keys(data[0])
    
    // Create CSV content
    const csvContent = [
      headers.join(','), // Header row
      ...data.map(row => 
        headers.map(header => {
          const value = row[header]
          // Escape commas and quotes in CSV
          if (typeof value === 'string' && (value.includes(',') || value.includes('"'))) {
            return `"${value.replace(/"/g, '""')}"`
          }
          return value
        }).join(',')
      )
    ].join('\n')
    
    // Download CSV
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `${filename}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
  
  const exportToExcel = () => {
    if (!data || data.length === 0) return
    
    const worksheet = XLSX.utils.json_to_sheet(data)
    const workbook = XLSX.utils.book_new()
    
    // Auto-size columns
    const colWidths = Object.keys(data[0]).map(key => ({
      wch: Math.max(
        key.length,
        ...data.map(row => String(row[key] || '').length)
      )
    }))
    worksheet['!cols'] = colWidths
    
    XLSX.utils.book_append_sheet(workbook, worksheet, 'Data')
    XLSX.writeFile(workbook, `${filename}.xlsx`)
  }
  
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant={variant} size={size}>
          <IconDownload />
          <span className="hidden lg:inline">Export Data</span>
          <span className="lg:hidden">Export</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem onClick={exportToCSV}>
          <IconFileText className="mr-2 h-4 w-4" />
          Download as CSV
        </DropdownMenuItem>
        <DropdownMenuItem onClick={exportToExcel}>
          <IconFileSpreadsheet className="mr-2 h-4 w-4" />
          Download as Excel
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled>
          <span className="text-muted-foreground">JSON export coming soon</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
