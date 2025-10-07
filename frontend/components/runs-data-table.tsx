"use client"

import * as React from "react"
import { useTransition } from "react"
import {
  IconChevronDown,
  IconChevronLeft,
  IconChevronRight,
  IconChevronsLeft,
  IconChevronsRight,
  IconDotsVertical,
  IconLayoutColumns,
  IconPlus,
  IconLoader,
  IconRefresh,
} from "@tabler/icons-react"
import {
  ColumnDef,
  ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFacetedRowModel,
  getFacetedUniqueValues,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  Row,
  SortingState,
  useReactTable,
  VisibilityState,
} from "@tanstack/react-table"
import { format } from "date-fns"
import { z } from "zod"

import { useGetRuns } from "@/hooks/getRuns"
import { useGetAllWorkerAnalytics } from "@/hooks/getRunAnalytics"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import { DataTableExport } from "@/components/export-data-table"
import { useRouter } from "next/navigation"

// Define the schema for runs data with analytics
export const runsDataSchema = z.object({
  id: z.string(),
  runId: z.string(),
  date: z.string(),
  status: z.string(),
  created_at: z.string(),
  // Analytics data (will be fetched separately)
  totalTransactions: z.number().default(0),
  successfulUpsells: z.number().default(0),
  successfulUpsizes: z.number().default(0),
  totalRevenue: z.number().default(0),
})

type RunsData = z.infer<typeof runsDataSchema>

const getStatusBadgeVariant = (status: string) => {
  switch (status.toLowerCase()) {
    case 'ready':
    case 'completed':
      return 'default' as const
    case 'processing':
    case 'uploading':
      return 'secondary' as const
    case 'failed':
    case 'error':
      return 'destructive' as const
    default:
      return 'outline' as const
  }
}

const getStatusColor = (status: string) => {
  switch (status.toLowerCase()) {
    case 'ready':
    case 'completed':
      return 'text-green-600 bg-green-50'
    case 'processing':
    case 'uploading':
      return 'text-blue-600 bg-blue-50'
    case 'failed':
    case 'error':
      return 'text-red-600 bg-red-50'
    default:
      return 'text-gray-600 bg-gray-50'
  }
}

const columns: ColumnDef<RunsData>[] = [
  {
    id: "select",
    header: ({ table }) => (
      <div className="flex items-center justify-center">
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      </div>
    ),
    cell: ({ row }) => (
      <div className="flex items-center justify-center">
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      </div>
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "date",
    header: "Run Date",
    cell: ({ row }) => {
      const date = new Date(row.original.date)
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    },
    enableHiding: false,
  },
  {
    accessorKey: "runId",
    header: "Run ID",
    cell: ({ row }) => (
      <Badge variant="outline" className="text-muted-foreground px-1.5 font-mono text-xs">
        {row.original.runId.slice(0, 8)}...
      </Badge>
    ),
    enableHiding: false,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => (
      <Badge 
        variant={getStatusBadgeVariant(row.original.status)}
        className={`capitalize ${getStatusColor(row.original.status)}`}
      >
        {row.original.status}
      </Badge>
    ),
  },
  {
    accessorKey: "totalTransactions",
    header: () => <div className="text-center">Transactions</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium">
        {row.original.totalTransactions.toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: "successfulUpsells",
    header: () => <div className="text-center">Successful Upsells</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium text-green-600">
        {row.original.successfulUpsells.toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: "successfulUpsizes",
    header: () => <div className="text-center">Successful Upsizes</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium text-blue-600">
        {row.original.successfulUpsizes.toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: "totalRevenue",
    header: () => <div className="text-center">Est. Revenue</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium text-emerald-600">
        ${row.original.totalRevenue.toFixed(2)}
      </div>
    ),
  },
  {
    id: "actions",
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="data-[state=open]:bg-muted text-muted-foreground flex size-8 dropdown-trigger"
            size="icon"
          >
            <IconDotsVertical />
            <span className="sr-only">Open menu</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          <DropdownMenuItem onClick={() => window.open(`/reports/${row.original.runId}`, '_blank')}>
            View Report
          </DropdownMenuItem>
          <DropdownMenuItem>
            View Analytics
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="text-red-600">
            Delete Run
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
]

// Worker name mapping
const workerNameMap: Record<string, string> = {
  "234ad11f-ceb8-4aea-b77d-2bf814fbcc70": "Sharon",
  "48f43602-ae51-4104-ab64-780d8f475bba": "Emily B",
  "639effce-e0dc-4283-bd6e-fa4dfd5910b8": "Adrijana",
  "7716dd87-ad7e-4419-830c-2161fe7db19b": "Latasha",
  "80b84d5e-59e2-4e3d-af7e-78f2544cbb23": "Jamarie Moore",
  "946c2ae8-5fe2-4d39-ae2f-286be9d09d7d": "Jalissa",
  "9bd60a00-4611-46f9-8285-bb329d871775": "Mario",
  "a52f9c84-9556-4171-b6f3-c149837cd54a": "Malaika",
  "a8b39309-16f9-4d52-b542-e3f8e1033a02": "Kayla",
  "ea6bc885-4e3c-423f-a333-5223624b90d1": "Cayden",
  "ffec99f2-ec72-401a-b799-ecc41724b6b1": "Jacob"
}

// Operator-specific columns for the "By Operator" tab
const operatorColumns: ColumnDef<any>[] = [
  {
    id: "select",
    header: ({ table }) => (
      <div className="flex items-center justify-center">
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      </div>
    ),
    cell: ({ row }) => (
      <div className="flex items-center justify-center">
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      </div>
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "run_date",
    header: "Run Date",
    cell: ({ row }) => {
      const date = new Date(row.original.run_date)
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    },
    enableHiding: false,
  },
  {
    accessorKey: "run_id",
    header: "Run ID",
    cell: ({ row }) => (
      <Badge variant="outline" className="text-muted-foreground px-1.5 font-mono text-xs">
        {row.original.run_id.slice(0, 8)}...
      </Badge>
    ),
  },
  {
    accessorKey: "worker_id",
    header: "Operator",
    cell: ({ row }) => (
      <Badge variant="secondary" className="bg-blue-100 text-blue-800">
        {workerNameMap[row.original.worker_id] || row.original.worker_id}
      </Badge>
    ),
  },
  {
    accessorKey: "total_transactions",
    header: () => <div className="text-center">Transactions</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium">
        {row.original.total_transactions.toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: "upsell_successes",
    header: () => <div className="text-center">Successful Upsells</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium text-green-600">
        {row.original.upsell_successes.toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: "upsize_successes",
    header: () => <div className="text-center">Successful Upsizes</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium text-blue-600">
        {row.original.upsize_successes.toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: "total_revenue",
    header: () => <div className="text-center">Est. Revenue</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium text-emerald-600">
        ${row.original.total_revenue.toFixed(2)}
      </div>
    ),
  },
  {
    id: "actions",
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="data-[state=open]:bg-muted text-muted-foreground flex size-8 dropdown-trigger"
            size="icon"
          >
            <IconDotsVertical />
            <span className="sr-only">Open menu</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          <DropdownMenuItem onClick={() => window.open(`/reports/${row.original.run_id}`, '_blank')}>
            View Full Report
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => window.open(`/reports/${row.original.run_id}?operator=${row.original.worker_id}`, '_blank')}>
            View Operator Report
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="text-red-600">
            Delete Run
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
]

function SimpleRow({ 
  row, 
  index, 
  isPending,
  onRowClick 
}: { 
  row: Row<any>
  index: number
  isPending: boolean
  onRowClick: (runId: string, runDate: string) => void
}) {
  const handleRowClick = (e: React.MouseEvent) => {
    // Don't trigger row click if clicking on action buttons or checkboxes
    if ((e.target as HTMLElement).closest('.dropdown-trigger, input[type="checkbox"]')) {
      return
    }
    // Handle both runs data and worker data structures
    const runId = row.original.runId || row.original.run_id
    const runDate = row.original.date || row.original.run_date
    onRowClick(runId, runDate)
  }

  return (
    <TableRow 
      data-state={row.getIsSelected() && "selected"}
      className={`transition-all duration-300 ease-in-out cursor-pointer hover:bg-muted/50 ${
        isPending ? 'scale-[0.98]' : 'scale-100'
      }`}
      style={{
        animationDelay: `${index * 50}ms`,
        animationFillMode: 'both'
      }}
      onClick={handleRowClick}
    >
      {row.getVisibleCells().map((cell) => (
        <TableCell 
          key={cell.id}
          className="transition-all duration-200 ease-in-out"
        >
          {flexRender(cell.column.columnDef.cell, cell.getContext())}
        </TableCell>
      ))}
    </TableRow>
  )
}

interface RunsDataTableProps {
  locationId?: string
  limit?: number
}

// Function to process runs data with analytics
const processRunsData = (runs: any[]): RunsData[] => {
  return runs.map((run) => ({
    id: run.id,
    runId: run.runId,
    date: run.date,
    status: run.status,
    created_at: run.created_at,
    totalTransactions: run.total_transcriptions || 0,
    successfulUpsells: run.successful_upsells || 0,
    successfulUpsizes: run.successful_upsizes || 0,
    totalRevenue: run.total_revenue || 0,
  }))
}

export function RunsDataTable({ locationId, limit = 50 }: RunsDataTableProps) {
  const [rowSelection, setRowSelection] = React.useState({})
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({})
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [pagination, setPagination] = React.useState({
    pageIndex: 0,
    pageSize: 10,
  })
  const [globalFilter, setGlobalFilter] = React.useState("")
  const [startDateTime, setStartDateTime] = React.useState<string>("")
  const [endDateTime, setEndDateTime] = React.useState<string>("")
  const [selectedOperatorId, setSelectedOperatorId] = React.useState<string>("")
  const [isPending, startTransition] = useTransition()
  const [runsData, setRunsData] = React.useState<RunsData[]>([])
  const [workerData, setWorkerData] = React.useState<any[]>([])
  const router = useRouter()
  const [activeTab, setActiveTab] = React.useState<string>('runs')

  // Fetch runs data using the hook
  const { 
    data: runsResponse, 
    isLoading, 
    isError, 
    error, 
    refetch,
    isRefetching 
  } = useGetRuns(locationId, { limit })

  // Fetch worker analytics data
  const { 
    data: workerResponse, 
    isLoading: isLoadingWorkers, 
    isError: isErrorWorkers, 
    error: errorWorkers, 
    refetch: refetchWorkers,
    isRefetching: isRefetchingWorkers 
  } = useGetAllWorkerAnalytics()

  // Process runs data with analytics when it changes
  React.useEffect(() => {
    if (runsResponse?.runs) {
      const processedData = processRunsData(runsResponse.runs)
      setRunsData(processedData)
    }
  }, [runsResponse])

  // Process worker analytics data when it changes
  React.useEffect(() => {
    if (workerResponse?.success && workerResponse.data) {
      setWorkerData(workerResponse.data)
    }
  }, [workerResponse])

  // Filter data based on global filter
  const filteredData = React.useMemo(() => {
    const gf = globalFilter.toLowerCase()
    const hasRange = !!startDateTime || !!endDateTime
    const start = startDateTime ? new Date(startDateTime) : null
    const end = endDateTime ? new Date(endDateTime) : null

    return runsData.filter((run) => {
      const matchesGlobal = gf
        ? run.runId.toLowerCase().includes(gf) ||
          run.status.toLowerCase().includes(gf) ||
          run.date.toLowerCase().includes(gf)
        : true

      if (!hasRange) return matchesGlobal

      const runDate = new Date(run.date)
      if (start && runDate < start) return false
      if (end && runDate > end) return false
      return matchesGlobal
    })
  }, [runsData, globalFilter, startDateTime, endDateTime])

  // Filter worker data based on global filter
  const filteredWorkerData = React.useMemo(() => {
    const gf = globalFilter.toLowerCase()
    const byText = (w: any) =>
      !gf ||
      w.run_id.toLowerCase().includes(gf) ||
      w.worker_id.toLowerCase().includes(gf) ||
      w.run_date.toLowerCase().includes(gf) ||
      (workerNameMap[w.worker_id] && workerNameMap[w.worker_id].toLowerCase().includes(gf))

    const byOperator = (w: any) => !selectedOperatorId || w.worker_id === selectedOperatorId

    return workerData.filter((w) => byText(w) && byOperator(w))
  }, [workerData, globalFilter, selectedOperatorId])

  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
      columnVisibility,
      rowSelection,
      columnFilters,
      pagination,
      globalFilter,
    },
    getRowId: (row) => row.id,
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onPaginationChange: setPagination,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
  })

  // Operator table for the "By Operator" tab
  const operatorTable = useReactTable({
    data: filteredWorkerData,
    columns: operatorColumns,
    state: {
      sorting,
      columnVisibility,
      rowSelection,
      columnFilters,
      pagination,
      globalFilter,
    },
    getRowId: (row) => row.id,
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onPaginationChange: setPagination,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
  })

  const handleRefresh = () => {
    startTransition(() => {
      refetch()
      refetchWorkers()
    })
  }

  const handleRowClick = (runId: string, runDate: string) => {
    router.push(`/reports/${runId}`)
  }

  if (isError) {
    return (
      <div className="px-4 lg:px-6">
        <div className="flex flex-col items-center justify-center p-8 text-center border rounded-lg">
          <div className="text-red-600 mb-2">Error loading runs</div>
          <div className="text-sm text-muted-foreground mb-4">
            {error?.message || 'Failed to fetch runs data'}
          </div>
          <Button onClick={handleRefresh} variant="outline">
            <IconRefresh className="mr-2 h-4 w-4" />
            Try Again
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 lg:px-6">
      <Tabs defaultValue="runs" value={activeTab} onValueChange={setActiveTab} className="w-full">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-base font-medium">Performance Data</h3>
            <p className="text-muted-foreground text-sm">
              {isLoading ? 'Loading...' : `${runsData.length} runs found`}
              {!isLoading && runsData.length > 0 && (
                <span className="ml-2">• Click any row to view detailed analytics</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              onClick={handleRefresh} 
              variant="outline" 
              size="sm"
              disabled={isLoading || isRefetching || isLoadingWorkers || isRefetchingWorkers}
            >
              {isLoading || isRefetching || isLoadingWorkers || isRefetchingWorkers ? (
                <IconLoader className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <IconRefresh className="mr-2 h-4 w-4" />
              )}
              <span className="hidden lg:inline">Refresh</span>
            </Button>
            <div className="hidden md:flex items-center gap-2">
              <Label className="text-xs text-muted-foreground">Operator</Label>
              <Select value={selectedOperatorId || 'all'} onValueChange={(v) => setSelectedOperatorId(v === 'all' ? '' : v)}>
                <SelectTrigger className="h-8 w-56">
                  <SelectValue placeholder="All operators" />
                </SelectTrigger>
                <SelectContent side="top">
                  <SelectItem value="all">All operators</SelectItem>
                  {Object.entries(workerNameMap).map(([id, name]) => (
                    <SelectItem key={id} value={id}>{name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {selectedOperatorId && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedOperatorId("")}
                >
                  Clear
                </Button>
              )}
            </div>
            <div className="hidden md:flex items-center gap-2">
              <Label className="text-xs text-muted-foreground">From</Label>
              <Input
                type="datetime-local"
                value={startDateTime}
                onChange={(e) => setStartDateTime(e.target.value)}
                className="h-8 w-56"
              />
              <Label className="text-xs text-muted-foreground">To</Label>
              <Input
                type="datetime-local"
                value={endDateTime}
                onChange={(e) => setEndDateTime(e.target.value)}
                className="h-8 w-56"
              />
              {(startDateTime || endDateTime) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => { setStartDateTime(""); setEndDateTime("") }}
                >
                  Clear
                </Button>
              )}
            </div>
            <DataTableExport 
              data={activeTab === 'by-operator' ? filteredWorkerData : filteredData} 
              filename={`${activeTab === 'by-operator' ? 'operator-analytics' : 'runs-data'}-${new Date().toISOString().split('T')[0]}`} 
            />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm">
                  <IconLayoutColumns />
                  <span className="hidden lg:inline">Columns</span>
                  <IconChevronDown />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                {table
                  .getAllColumns()
                  .filter(
                    (column) =>
                      typeof column.accessorFn !== "undefined" &&
                      column.getCanHide()
                  )
                  .map((column) => {
                    return (
                      <DropdownMenuCheckboxItem
                        key={column.id}
                        className="capitalize"
                        checked={column.getIsVisible()}
                        onCheckedChange={(value) =>
                          column.toggleVisibility(!!value)
                        }
                      >
                        {column.id}
                      </DropdownMenuCheckboxItem>
                    )
                  })}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="runs">Runs</TabsTrigger>
          <TabsTrigger value="by-operator">By Operator</TabsTrigger>
        </TabsList>

        <TabsContent value="runs" className="space-y-4">
          {/* Search, mobile operator and mobile date range */}
          <div className="flex items-center gap-4 flex-wrap">
            <Input
              placeholder="Search runs..."
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="max-w-sm"
            />
            <div className="flex md:hidden items-center gap-2 w-full">
              <Select value={selectedOperatorId || 'all'} onValueChange={(v) => setSelectedOperatorId(v === 'all' ? '' : v)}>
                <SelectTrigger className="h-8 w-full">
                  <SelectValue placeholder="All operators" />
                </SelectTrigger>
                <SelectContent side="top">
                  <SelectItem value="all">All operators</SelectItem>
                  {Object.entries(workerNameMap).map(([id, name]) => (
                    <SelectItem key={id} value={id}>{name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex md:hidden items-center gap-2 w-full">
              <Input
                type="datetime-local"
                value={startDateTime}
                onChange={(e) => setStartDateTime(e.target.value)}
                className="h-8 flex-1"
              />
              <Input
                type="datetime-local"
                value={endDateTime}
                onChange={(e) => setEndDateTime(e.target.value)}
                className="h-8 flex-1"
              />
              {(startDateTime || endDateTime) && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => { setStartDateTime(""); setEndDateTime("") }}
                >
                  Clear
                </Button>
              )}
            </div>
          </div>

          {/* Table */}
          <div className={`overflow-hidden rounded-lg border transition-all duration-300 ease-in-out ${
            isPending || isLoading ? 'shadow-sm' : 'shadow-md'
          }`}>
            <Table>
              <TableHeader className="bg-muted sticky top-0 z-10">
                {table.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => {
                      return (
                        <TableHead key={header.id} colSpan={header.colSpan}>
                          {header.isPlaceholder
                            ? null
                            : flexRender(
                                header.column.columnDef.header,
                                header.getContext()
                              )}
                        </TableHead>
                      )
                    })}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody className={`transition-opacity duration-300 ${isPending || isLoading ? 'opacity-50' : 'opacity-100'}`}>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={columns.length} className="h-24 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <IconLoader className="h-4 w-4 animate-spin" />
                        Loading runs...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : table.getRowModel().rows?.length ? (
                  table.getRowModel().rows.map((row, index) => (
                    <SimpleRow 
                      key={row.id} 
                      row={row} 
                      index={index}
                      isPending={isPending || isRefetching}
                      onRowClick={handleRowClick}
                    />
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={columns.length}
                      className="h-24 text-center"
                    >
                      No runs found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <div className="text-muted-foreground hidden flex-1 text-sm lg:flex">
              {table.getFilteredSelectedRowModel().rows.length} of{" "}
              {table.getFilteredRowModel().rows.length} row(s) selected.
            </div>
            <div className="flex w-full items-center gap-8 lg:w-fit">
              <div className="hidden items-center gap-2 lg:flex">
                <Label htmlFor="rows-per-page" className="text-sm font-medium">
                  Rows per page
                </Label>
                <Select
                  value={`${table.getState().pagination.pageSize}`}
                  onValueChange={(value) => {
                    table.setPageSize(Number(value))
                  }}
                >
                  <SelectTrigger className="w-20" id="rows-per-page">
                    <SelectValue
                      placeholder={table.getState().pagination.pageSize}
                    />
                  </SelectTrigger>
                  <SelectContent side="top">
                    {[10, 20, 30, 40, 50].map((pageSize) => (
                      <SelectItem key={pageSize} value={`${pageSize}`}>
                        {pageSize}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex w-fit items-center justify-center text-sm font-medium">
                Page {table.getState().pagination.pageIndex + 1} of{" "}
                {table.getPageCount()}
              </div>
              <div className="ml-auto flex items-center gap-2 lg:ml-0">
                <Button
                  variant="outline"
                  className="hidden h-8 w-8 p-0 lg:flex"
                  onClick={() => table.setPageIndex(0)}
                  disabled={!table.getCanPreviousPage()}
                >
                  <span className="sr-only">Go to first page</span>
                  <IconChevronsLeft />
                </Button>
                <Button
                  variant="outline"
                  className="size-8"
                  size="icon"
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                >
                  <span className="sr-only">Go to previous page</span>
                  <IconChevronLeft />
                </Button>
                <Button
                  variant="outline"
                  className="size-8"
                  size="icon"
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                >
                  <span className="sr-only">Go to next page</span>
                  <IconChevronRight />
                </Button>
                <Button
                  variant="outline"
                  className="hidden size-8 lg:flex"
                  size="icon"
                  onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                  disabled={!table.getCanNextPage()}
                >
                  <span className="sr-only">Go to last page</span>
                  <IconChevronsRight />
                </Button>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="by-operator" className="space-y-4">
          {/* Search */}
          <div className="flex items-center gap-4">
            <Input
              placeholder="Search runs..."
              value={globalFilter}
              onChange={(e) => setGlobalFilter(e.target.value)}
              className="max-w-sm"
            />
          </div>

          {/* Operator Table */}
          <div className={`overflow-hidden rounded-lg border transition-all duration-300 ease-in-out ${
            isPending || isLoading ? 'shadow-sm' : 'shadow-md'
          }`}>
            <Table>
              <TableHeader className="bg-muted sticky top-0 z-10">
                {operatorTable.getHeaderGroups().map((headerGroup) => (
                  <TableRow key={headerGroup.id}>
                    {headerGroup.headers.map((header) => {
                      return (
                        <TableHead key={header.id} colSpan={header.colSpan}>
                          {header.isPlaceholder
                            ? null
                            : flexRender(
                                header.column.columnDef.header,
                                header.getContext()
                              )}
                        </TableHead>
                      )
                    })}
                  </TableRow>
                ))}
              </TableHeader>
              <TableBody className={`transition-opacity duration-300 ${isPending || isLoadingWorkers ? 'opacity-50' : 'opacity-100'}`}>
                {isLoadingWorkers ? (
                  <TableRow>
                    <TableCell colSpan={operatorColumns.length} className="h-24 text-center">
                      <div className="flex items-center justify-center gap-2">
                        <IconLoader className="h-4 w-4 animate-spin" />
                        Loading worker analytics...
                      </div>
                    </TableCell>
                  </TableRow>
                ) : operatorTable.getRowModel().rows?.length ? (
                  operatorTable.getRowModel().rows.map((row, index) => (
                    <SimpleRow 
                      key={row.id} 
                      row={row} 
                      index={index}
                      isPending={isPending || isRefetchingWorkers}
                      onRowClick={handleRowClick}
                    />
                  ))
                ) : (
                  <TableRow>
                    <TableCell
                      colSpan={operatorColumns.length}
                      className="h-24 text-center"
                    >
                      No runs found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <div className="text-muted-foreground hidden flex-1 text-sm lg:flex">
              {operatorTable.getFilteredSelectedRowModel().rows.length} of{" "}
              {operatorTable.getFilteredRowModel().rows.length} row(s) selected.
            </div>
            <div className="flex w-full items-center gap-8 lg:w-fit">
              <div className="hidden items-center gap-2 lg:flex">
                <Label htmlFor="rows-per-page-2" className="text-sm font-medium">
                  Rows per page
                </Label>
                <Select
                  value={`${operatorTable.getState().pagination.pageSize}`}
                  onValueChange={(value) => {
                    operatorTable.setPageSize(Number(value))
                  }}
                >
                  <SelectTrigger className="w-20" id="rows-per-page-2">
                    <SelectValue
                      placeholder={operatorTable.getState().pagination.pageSize}
                    />
                  </SelectTrigger>
                  <SelectContent side="top">
                    {[10, 20, 30, 40, 50].map((pageSize) => (
                      <SelectItem key={pageSize} value={`${pageSize}`}>
                        {pageSize}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex w-fit items-center justify-center text-sm font-medium">
                Page {operatorTable.getState().pagination.pageIndex + 1} of{" "}
                {operatorTable.getPageCount()}
              </div>
              <div className="ml-auto flex items-center gap-2 lg:ml-0">
                <Button
                  variant="outline"
                  className="hidden h-8 w-8 p-0 lg:flex"
                  onClick={() => operatorTable.setPageIndex(0)}
                  disabled={!operatorTable.getCanPreviousPage()}
                >
                  <span className="sr-only">Go to first page</span>
                  <IconChevronsLeft />
                </Button>
                <Button
                  variant="outline"
                  className="size-8"
                  size="icon"
                  onClick={() => operatorTable.previousPage()}
                  disabled={!operatorTable.getCanPreviousPage()}
                >
                  <span className="sr-only">Go to previous page</span>
                  <IconChevronLeft />
                </Button>
                <Button
                  variant="outline"
                  className="size-8"
                  size="icon"
                  onClick={() => operatorTable.nextPage()}
                  disabled={!operatorTable.getCanNextPage()}
                >
                  <span className="sr-only">Go to next page</span>
                  <IconChevronRight />
                </Button>
                <Button
                  variant="outline"
                  className="hidden size-8 lg:flex"
                  size="icon"
                  onClick={() => operatorTable.setPageIndex(operatorTable.getPageCount() - 1)}
                  disabled={!operatorTable.getCanNextPage()}
                >
                  <span className="sr-only">Go to last page</span>
                  <IconChevronsRight />
                </Button>
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
