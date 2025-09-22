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
  IconRefresh,
  IconLoader,
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

// Define the schema for run data
export const runSchema = z.object({
  id: z.string(),
  runId: z.string(),
  date: z.string(),
  status: z.string(),
  created_at: z.string(),
  org_id: z.string(),
  location_id: z.string(),
})

type RunData = z.infer<typeof runSchema>

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

const columns: ColumnDef<RunData>[] = [
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
    accessorKey: "created_at",
    header: "Created",
    cell: ({ row }) => {
      const date = new Date(row.original.created_at)
      return (
        <div className="text-sm">
          <div>{format(date, "MMM dd, yyyy")}</div>
          <div className="text-muted-foreground text-xs">{format(date, "HH:mm")}</div>
        </div>
      )
    },
  },
  {
    id: "actions",
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="data-[state=open]:bg-muted text-muted-foreground flex size-8"
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

function SimpleRow({ 
  row, 
  index, 
  isPending 
}: { 
  row: Row<RunData>
  index: number
  isPending: boolean
}) {
  return (
    <TableRow 
      data-state={row.getIsSelected() && "selected"}
      className={`transition-all duration-300 ease-in-out ${
        isPending ? 'scale-[0.98]' : 'scale-100'
      }`}
      style={{
        animationDelay: `${index * 50}ms`,
        animationFillMode: 'both'
      }}
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

interface RunsTableProps {
  locationId: string
  limit?: number
  showLocationInfo?: boolean
}

export function RunsTable({ locationId, limit = 50, showLocationInfo = false }: RunsTableProps) {
  const [rowSelection, setRowSelection] = React.useState({})
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({})
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([])
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [pagination, setPagination] = React.useState({
    pageIndex: 0,
    pageSize: 10,
  })
  const [globalFilter, setGlobalFilter] = React.useState("")
  const [isPending, startTransition] = useTransition()

  // Fetch runs data using the hook
  const { 
    data: runsResponse, 
    isLoading, 
    isError, 
    error, 
    refetch,
    isRefetching 
  } = useGetRuns(locationId, { limit })

  const runs = runsResponse?.runs || []

  // Filter data based on global filter
  const filteredData = React.useMemo(() => {
    if (!globalFilter) return runs

    return runs.filter((run) =>
      run.runId.toLowerCase().includes(globalFilter.toLowerCase()) ||
      run.status.toLowerCase().includes(globalFilter.toLowerCase()) ||
      run.date.toLowerCase().includes(globalFilter.toLowerCase())
    )
  }, [runs, globalFilter])

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

  const handleRefresh = () => {
    startTransition(() => {
      refetch()
    })
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <div className="text-red-600 mb-2">Error loading runs</div>
        <div className="text-sm text-muted-foreground mb-4">
          {error?.message || 'Failed to fetch runs data'}
        </div>
        <Button onClick={handleRefresh} variant="outline">
          <IconRefresh className="mr-2 h-4 w-4" />
          Try Again
        </Button>
      </div>
    )
  }

  return (
    <div className="w-full space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold">Runs</h3>
          <p className="text-muted-foreground">
            {isLoading ? 'Loading...' : `${runs.length} runs found`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            onClick={handleRefresh} 
            variant="outline" 
            size="sm"
            disabled={isLoading || isRefetching}
          >
            {isLoading || isRefetching ? (
              <IconLoader className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <IconRefresh className="mr-2 h-4 w-4" />
            )}
            Refresh
          </Button>
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
          <Button variant="outline" size="sm">
            <IconPlus />
            <span className="hidden lg:inline">New Run</span>
          </Button>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-4">
        <Input
          placeholder="Search runs..."
          value={globalFilter}
          onChange={(e) => setGlobalFilter(e.target.value)}
          className="max-w-sm"
        />
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
      <div className="flex items-center justify-between px-4">
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
              <SelectTrigger size="sm" className="w-20" id="rows-per-page">
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
    </div>
  )
}
