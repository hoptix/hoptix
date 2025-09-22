/**
 * CSV Export Utilities
 */

export interface CSVColumn {
  key: string
  label: string
  transform?: (value: any, row?: any) => string
}

/**
 * Convert data to CSV format
 */
export function convertToCSV(data: any[], columns: CSVColumn[]): string {
  if (!data.length) return ''

  // Create header row
  const headers = columns.map(col => `"${col.label}"`).join(',')
  
  // Create data rows
  const rows = data.map(row => {
    return columns.map(col => {
      let value = row[col.key]
      
      // Apply transform if provided
      if (col.transform) {
        value = col.transform(value, row)
      }
      
      // Handle null/undefined values
      if (value === null || value === undefined) {
        value = ''
      }
      
      // Convert to string and escape quotes
      const stringValue = String(value).replace(/"/g, '""')
      
      return `"${stringValue}"`
    }).join(',')
  })
  
  return [headers, ...rows].join('\n')
}

/**
 * Download CSV file
 */
export function downloadCSV(csvContent: string, filename: string): void {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  
  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', filename)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }
}

/**
 * Format date for CSV
 */
export function formatDateForCSV(dateString: string): string {
  if (!dateString) return ''
  try {
    const date = new Date(dateString)
    return date.toISOString().slice(0, 19).replace('T', ' ')
  } catch {
    return dateString
  }
}

/**
 * Format duration for CSV
 */
export function formatDurationForCSV(startTime: string, endTime: string): string {
  if (!startTime || !endTime) return ''
  try {
    const start = new Date(startTime)
    const end = new Date(endTime)
    const durationMs = end.getTime() - start.getTime()
    const minutes = Math.floor(durationMs / 60000)
    const seconds = Math.floor((durationMs % 60000) / 1000)
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  } catch {
    return ''
  }
}

/**
 * Clean JSON field for CSV
 */
export function cleanJSONForCSV(value: any): string {
  if (!value) return ''
  if (typeof value === 'object') {
    return JSON.stringify(value).replace(/\n/g, ' ').replace(/\r/g, ' ')
  }
  return String(value).replace(/\n/g, ' ').replace(/\r/g, ' ')
}
