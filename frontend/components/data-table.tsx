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
  IconTrendingUp,
  IconTrophy,
  IconMedal,
  IconAward,
  IconStar,
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
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts"
import { toast } from "sonner"
import { z } from "zod"

import { useIsMobile } from "@/hooks/use-mobile"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer"
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
import { DataTableExport } from "@/components/export-data-table"
import { Separator } from "@/components/ui/separator"
import { CalendarIcon } from "@radix-ui/react-icons"
import { format } from "date-fns"
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
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

export const schema = z.object({
  id: z.number(),
  date: z.string(),
  runId: z.string(),
  operatorName: z.string(),
  restaurantName: z.string(),
  restaurantLocation: z.string(),
  totalChances: z.number(),
  totalOffers: z.number(),
  successfulOffers: z.number(),
  offerRate: z.number(),
  conversionRate: z.number(),
  totalSuccessfulItems: z.number(),
})



const columns: ColumnDef<z.infer<typeof schema>>[] = [
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
    header: "Date",
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
      <Badge variant="outline" className="text-muted-foreground px-1.5 font-mono">
        {row.original.runId}
      </Badge>
    ),
    enableHiding: false,
  },
  {
    accessorKey: "operatorName",
    header: "Operator",
    cell: ({ row }) => (
      <div className="font-medium">
        {row.original.operatorName}
      </div>
    ),
  },
  {
    accessorKey: "restaurantName",
    header: "Restaurant",
    cell: ({ row }) => (
      <div className="font-medium">
        <div>{row.original.restaurantName}</div>
        <div className="text-xs text-muted-foreground">{row.original.restaurantLocation}</div>
      </div>
    ),
  },
  {
    accessorKey: "totalChances",
    header: () => <div className="text-center">Total Chances</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium">
        {row.original.totalChances.toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: "offerRate",
    header: () => <div className="text-center">Offer %</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium">
        {row.original.offerRate.toFixed(1)}%
      </div>
    ),
  },
  {
    accessorKey: "conversionRate",
    header: () => <div className="text-center">Conversion %</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium">
        {row.original.conversionRate.toFixed(1)}%
      </div>
    ),
  },
  {
    accessorKey: "totalSuccessfulItems",
    header: () => <div className="text-center">Total Successful Items</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium">
        {row.original.totalSuccessfulItems.toLocaleString()}
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
            className="data-[state=open]:bg-muted text-muted-foreground flex size-8"
            size="icon"
          >
            <IconDotsVertical />
            <span className="sr-only">Open menu</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          <DropdownMenuItem>View Details</DropdownMenuItem>
          <DropdownMenuItem onClick={() => window.open(`/reports/${row.original.runId}`, '_blank')}>
            Export Report
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem>Archive</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    ),
  },
]

// Operator-specific columns for the "By Operator" tab
const operatorColumns: ColumnDef<z.infer<typeof schema>>[] = [
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
    accessorKey: "operatorName",
    header: "Operator",
    cell: ({ row }) => (
      <div className="font-medium">
        {row.original.operatorName}
      </div>
    ),
    enableHiding: false,
  },
  {
    accessorKey: "date",
    header: "Date",
    cell: ({ row }) => {
      const date = new Date(row.original.date)
      return date.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    },
  },
  {
    accessorKey: "runId",
    header: "Run ID",
    cell: ({ row }) => (
      <Badge variant="outline" className="text-muted-foreground px-1.5 font-mono">
        {row.original.runId}
      </Badge>
    ),
  },
  {
    accessorKey: "restaurantName",
    header: "Restaurant",
    cell: ({ row }) => (
      <div className="font-medium">
        <div>{row.original.restaurantName}</div>
        <div className="text-xs text-muted-foreground">{row.original.restaurantLocation}</div>
      </div>
    ),
  },
  {
    accessorKey: "totalChances",
    header: () => <div className="text-center">Total Chances</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium">
        {row.original.totalChances.toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: "totalOffers",
    header: () => <div className="text-center">Total Offers</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium">
        {row.original.totalOffers.toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: "totalSuccessfulItems",
    header: () => <div className="text-center">Successful Items</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium">
        {row.original.totalSuccessfulItems.toLocaleString()}
      </div>
    ),
  },
  {
    accessorKey: "conversionRate",
    header: () => <div className="text-center">Conversion %</div>,
    cell: ({ row }) => (
      <div className="text-center font-medium">
        {row.original.conversionRate.toFixed(1)}%
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
            className="data-[state=open]:bg-muted text-muted-foreground flex size-8"
            size="icon"
          >
            <IconDotsVertical />
            <span className="sr-only">Open menu</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          <DropdownMenuItem onClick={() => window.open(`/reports/${row.original.runId}?operator=${row.original.operatorName}`, '_blank')}>
            View Operator Report
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => window.open(`/reports/${row.original.runId}`, '_blank')}>
            View Full Report
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem>Archive</DropdownMenuItem>
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
  row: Row<z.infer<typeof schema>>
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

// Top Performers Component
function TopPerformers({ 
  data, 
  period 
}: { 
  data: z.infer<typeof schema>[]
  period: 'weekly' | 'monthly'
}) {
  // Calculate operator performance metrics
  const operatorMetrics = React.useMemo(() => {
    const operatorStats = data.reduce((acc, row) => {
      const operator = row.operatorName
      if (!acc[operator]) {
        acc[operator] = {
          name: operator,
          totalOffers: 0,
          totalSuccesses: 0,
          totalChances: 0,
          transactions: 0,
          totalRevenue: 0
        }
      }
      
      acc[operator].totalOffers += row.totalOffers
      acc[operator].totalSuccesses += row.totalSuccessfulItems
      acc[operator].totalChances += row.totalChances
      acc[operator].transactions += 1
      acc[operator].totalRevenue += row.totalSuccessfulItems * 4.5 // Estimated revenue per success
      
      return acc
    }, {} as Record<string, any>)

    // Calculate performance scores and grades
    return Object.values(operatorStats).map((stats: any) => {
      const conversionRate = stats.totalOffers > 0 ? (stats.totalSuccesses / stats.totalOffers) * 100 : 0
      const offerRate = stats.totalChances > 0 ? (stats.totalOffers / stats.totalChances) * 100 : 0
      const avgSuccessPerTransaction = stats.transactions > 0 ? stats.totalSuccesses / stats.transactions : 0
      
      // Calculate overall performance score (0-100)
      const performanceScore = (conversionRate * 0.4) + (offerRate * 0.3) + (avgSuccessPerTransaction * 10 * 0.3)
      
      // Assign grade based on performance score
      let grade = 'F'
      let gradeColor = 'text-red-600 bg-red-50'
      if (performanceScore >= 90) {
        grade = 'A+'
        gradeColor = 'text-emerald-600 bg-emerald-50'
      } else if (performanceScore >= 85) {
        grade = 'A'
        gradeColor = 'text-emerald-600 bg-emerald-50'
      } else if (performanceScore >= 80) {
        grade = 'A-'
        gradeColor = 'text-green-600 bg-green-50'
      } else if (performanceScore >= 75) {
        grade = 'B+'
        gradeColor = 'text-green-600 bg-green-50'
      } else if (performanceScore >= 70) {
        grade = 'B'
        gradeColor = 'text-blue-600 bg-blue-50'
      } else if (performanceScore >= 65) {
        grade = 'B-'
        gradeColor = 'text-blue-600 bg-blue-50'
      } else if (performanceScore >= 60) {
        grade = 'C+'
        gradeColor = 'text-yellow-600 bg-yellow-50'
      } else if (performanceScore >= 55) {
        grade = 'C'
        gradeColor = 'text-yellow-600 bg-yellow-50'
      } else if (performanceScore >= 50) {
        grade = 'C-'
        gradeColor = 'text-orange-600 bg-orange-50'
      } else if (performanceScore >= 40) {
        grade = 'D'
        gradeColor = 'text-red-600 bg-red-50'
      }
      
      return {
        ...stats,
        conversionRate,
        offerRate,
        avgSuccessPerTransaction,
        performanceScore,
        grade,
        gradeColor
      }
    }).sort((a, b) => b.performanceScore - a.performanceScore)
  }, [data])

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1:
        return <IconTrophy className="h-6 w-6 text-yellow-500" />
      case 2:
        return <IconMedal className="h-6 w-6 text-gray-400" />
      case 3:
        return <IconAward className="h-6 w-6 text-amber-600" />
      default:
        return <IconStar className="h-5 w-5 text-muted-foreground" />
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-2xl font-bold">Top Performers - {period === 'weekly' ? 'This Week' : 'This Month'}</h3>
          <p className="text-muted-foreground">
            Operators ranked by overall performance score
          </p>
        </div>
        <Badge variant="outline" className="px-3 py-1">
          {operatorMetrics.length} Operators
        </Badge>
      </div>

      <div className="grid gap-4">
        {operatorMetrics.map((operator, index) => (
          <div
            key={operator.name}
            className={`p-6 rounded-lg border transition-all hover:shadow-md ${
              index < 3 ? 'bg-gradient-to-r from-blue-50 to-indigo-50 border-blue-200' : 'bg-white'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  {getRankIcon(index + 1)}
                  <span className="text-2xl font-bold text-muted-foreground">#{index + 1}</span>
                </div>
                <div>
                  <h4 className="text-xl font-semibold">{operator.name}</h4>
                  <p className="text-sm text-muted-foreground">{operator.transactions} transactions</p>
                </div>
              </div>
              
              <div className="flex items-center gap-6">
                <div className="text-right">
                  <div className="text-2xl font-bold">{operator.performanceScore.toFixed(1)}</div>
                  <div className="text-sm text-muted-foreground">Score</div>
                </div>
                <Badge className={`px-3 py-1 text-lg font-bold ${operator.gradeColor}`} variant="secondary">
                  {operator.grade}
                </Badge>
              </div>
            </div>
            
            <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <div className="text-sm text-muted-foreground">Conversion Rate</div>
                <div className="text-lg font-semibold">{operator.conversionRate.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Offer Rate</div>
                <div className="text-lg font-semibold">{operator.offerRate.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Avg Success/Transaction</div>
                <div className="text-lg font-semibold">{operator.avgSuccessPerTransaction.toFixed(1)}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">Est. Revenue</div>
                <div className="text-lg font-semibold">${operator.totalRevenue.toFixed(0)}</div>
              </div>
            </div>
          </div>
        ))}
        
        {operatorMetrics.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            <IconTrophy className="mx-auto h-12 w-12 mb-4 opacity-50" />
            <p>No performance data available yet</p>
            <p className="text-sm">Performance rankings will appear here after data collection</p>
          </div>
        )}
      </div>
    </div>
  )
}

export function DataTable({
  data,
  hideRestaurantFilter = false,
}: {
  data: z.infer<typeof schema>[]
  hideRestaurantFilter?: boolean
}) {
  const [rowSelection, setRowSelection] = React.useState({})
  const [columnVisibility, setColumnVisibility] =
    React.useState<VisibilityState>({})
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    []
  )
  const [sorting, setSorting] = React.useState<SortingState>([])
  const [pagination, setPagination] = React.useState({
    pageIndex: 0,
    pageSize: 10,
  })
  const [selectedOperator, setSelectedOperator] = React.useState<string>("all")
  const [selectedRestaurant, setSelectedRestaurant] = React.useState<string>("all")
  const [dateRange, setDateRange] = React.useState<{
    from: Date | undefined
    to: Date | undefined
  }>({
    from: undefined,
    to: undefined,
  })
  const [isPending, startTransition] = useTransition()
  const [isFiltering, setIsFiltering] = React.useState(false)

  // Get unique operators for filter
  const uniqueOperators = React.useMemo(() => {
    const operators = data.map(item => item.operatorName)
    return Array.from(new Set(operators)).sort()
  }, [data])

  // Get unique restaurants for filter
  const uniqueRestaurants = React.useMemo(() => {
    const restaurants = data.map(item => `${item.restaurantName} - ${item.restaurantLocation}`)
    return Array.from(new Set(restaurants)).sort()
  }, [data])

  // Debounced filter effects
  React.useEffect(() => {
    setIsFiltering(true)
    const timeoutId = setTimeout(() => {
      setIsFiltering(false)
    }, 300)

    return () => clearTimeout(timeoutId)
  }, [selectedOperator, selectedRestaurant, dateRange])

  // Filter data based on selected filters with transition
  const filteredData = React.useMemo(() => {
    let filtered = data

    // Filter by operator
    if (selectedOperator !== "all") {
      filtered = filtered.filter(item => item.operatorName === selectedOperator)
    }

    // Filter by restaurant
    if (selectedRestaurant !== "all") {
      filtered = filtered.filter(item => 
        `${item.restaurantName} - ${item.restaurantLocation}` === selectedRestaurant
      )
    }

    // Filter by date range
    if (dateRange.from || dateRange.to) {
      filtered = filtered.filter(item => {
        const itemDate = new Date(item.date)
        const fromMatch = !dateRange.from || itemDate >= dateRange.from
        const toMatch = !dateRange.to || itemDate <= dateRange.to
        return fromMatch && toMatch
      })
    }

    return filtered
  }, [data, selectedOperator, selectedRestaurant, dateRange])

  // Handlers with transitions
  const handleOperatorChange = (value: string) => {
    startTransition(() => {
      setSelectedOperator(value)
    })
  }

  const handleRestaurantChange = (value: string) => {
    startTransition(() => {
      setSelectedRestaurant(value)
    })
  }

  const handleDateRangeChange = (field: 'from' | 'to', date: Date | undefined) => {
    startTransition(() => {
      setDateRange(prev => ({ ...prev, [field]: date }))
    })
  }

  const handleClearDateRange = () => {
    startTransition(() => {
      setDateRange({ from: undefined, to: undefined })
    })
  }

  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
      columnVisibility,
      rowSelection,
      columnFilters,
      pagination,
    },
    getRowId: (row) => row.runId,
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
  })

  // Operator table for the "By Operator" tab
  const operatorTable = useReactTable({
    data: filteredData,
    columns: operatorColumns,
    state: {
      sorting,
      columnVisibility,
      rowSelection,
      columnFilters,
      pagination,
    },
    getRowId: (row) => `${row.runId}-${row.operatorName}`,
    enableRowSelection: true,
    onRowSelectionChange: setRowSelection,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onPaginationChange: setPagination,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFacetedRowModel: getFacetedRowModel(),
    getFacetedUniqueValues: getFacetedUniqueValues(),
  })



  return (
    <Tabs
      defaultValue="daily-metrics"
      className="w-full flex-col justify-start gap-6"
    >
      <div className="flex items-center justify-between px-4 lg:px-6">
        <Label htmlFor="view-selector" className="sr-only">
          View
        </Label>
        <Select defaultValue="daily-metrics">
          <SelectTrigger
            className="flex w-fit @4xl/main:hidden"
            id="view-selector"
          >
            <SelectValue placeholder="Select a view" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="daily-metrics">Daily Metrics</SelectItem>
            <SelectItem value="by-operator">By Operator</SelectItem>
            <SelectItem value="weekly-summary">Weekly Summary</SelectItem>
            <SelectItem value="monthly-trends">Monthly Trends</SelectItem>
          </SelectContent>
        </Select>
        <TabsList className="**:data-[slot=badge]:bg-muted-foreground/30 hidden **:data-[slot=badge]:size-5 **:data-[slot=badge]:rounded-full **:data-[slot=badge]:px-1 @4xl/main:flex">
          <TabsTrigger value="daily-metrics">Daily Metrics</TabsTrigger>
          <TabsTrigger value="by-operator">By Operator</TabsTrigger>
          <TabsTrigger value="weekly-summary">Weekly Summary</TabsTrigger>
          <TabsTrigger value="monthly-trends">Monthly Trends</TabsTrigger>
        </TabsList>
        <div className="flex items-center gap-2">
          <DataTableExport 
            data={filteredData} 
            filename={`daily-metrics-${new Date().toISOString().split('T')[0]}`} 
          />
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <IconLayoutColumns />
                <span className="hidden lg:inline">Customize Columns</span>
                <span className="lg:hidden">Columns</span>
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
            <span className="hidden lg:inline">Add Entry</span>
          </Button>
        </div>
      </div>
      <TabsContent
        value="daily-metrics"
        className="relative flex flex-col gap-4 overflow-auto px-4 lg:px-6"
      >
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="text-base font-medium">Daily Performance Data</h3>
            {(isPending || isFiltering) && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"></div>
                Filtering...
              </div>
            )}
          </div>
          
          {/* Filter Controls */}
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:gap-6">
            {/* Operator Filter */}
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:gap-2">
              <Label htmlFor="operator-filter" className="text-sm font-medium whitespace-nowrap">
                Operator:
              </Label>
              <Select value={selectedOperator} onValueChange={handleOperatorChange}>
                <SelectTrigger className="w-full lg:w-48" id="operator-filter" disabled={isPending}>
                  <SelectValue placeholder="All operators" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All operators</SelectItem>
                  {uniqueOperators.map((operator) => (
                    <SelectItem key={operator} value={operator}>
                      {operator}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Restaurant Filter - Only show if not hidden */}
            {!hideRestaurantFilter && (
              <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:gap-2">
                <Label htmlFor="restaurant-filter" className="text-sm font-medium whitespace-nowrap">
                  Restaurant:
                </Label>
                <Select value={selectedRestaurant} onValueChange={handleRestaurantChange}>
                  <SelectTrigger className="w-full lg:w-56" id="restaurant-filter" disabled={isPending}>
                    <SelectValue placeholder="All restaurants" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All restaurants</SelectItem>
                    {uniqueRestaurants.map((restaurant) => (
                      <SelectItem key={restaurant} value={restaurant}>
                        {restaurant}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            
            {/* Date Range Filter */}
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:gap-2">
              <Label className="text-sm font-medium whitespace-nowrap">
                Date Range:
              </Label>
              <div className="flex gap-2">
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className="w-full lg:w-36 justify-start text-left font-normal"
                      disabled={isPending}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {dateRange.from ? (
                        format(dateRange.from, "MMM dd, yyyy")
                      ) : (
                        <span>From date</span>
                      )}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={dateRange.from}
                      onSelect={(date: Date | undefined) => handleDateRangeChange('from', date)}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
                
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className="w-full lg:w-36 justify-start text-left font-normal"
                      disabled={isPending}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {dateRange.to ? (
                        format(dateRange.to, "MMM dd, yyyy")
                      ) : (
                        <span>To date</span>
                      )}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={dateRange.to}
                      onSelect={(date: Date | undefined) => handleDateRangeChange('to', date)}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
                
                {(dateRange.from || dateRange.to) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearDateRange}
                    className="px-2"
                    disabled={isPending}
                  >
                    Clear
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
        <div className={`overflow-hidden rounded-lg border transition-all duration-300 ease-in-out ${
          isPending || isFiltering ? 'shadow-sm' : 'shadow-md'
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
            <TableBody className={`transition-opacity duration-300 ${isPending || isFiltering ? 'opacity-50' : 'opacity-100'}`}>
              {table.getRowModel().rows?.length ? (
                table.getRowModel().rows.map((row, index) => (
                  <SimpleRow 
                    key={row.id} 
                    row={row} 
                    index={index}
                    isPending={isPending || isFiltering}
                  />
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={columns.length}
                    className="h-24 text-center"
                  >
                    No results.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
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
      <TabsContent
        value="by-operator"
        className="relative flex flex-col gap-4 overflow-auto px-4 lg:px-6"
      >
        <div className="flex flex-col gap-4">
          <div className="flex justify-between items-center">
            <h3 className="text-base font-medium">Operator Performance Data</h3>
            {(isPending || isFiltering) && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"></div>
                Filtering...
              </div>
            )}
          </div>
          
          {/* Filter Controls for Operator View */}
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:gap-6">
            {/* Operator Filter */}
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:gap-2">
              <Label htmlFor="operator-filter-2" className="text-sm font-medium whitespace-nowrap">
                Operator:
              </Label>
              <Select value={selectedOperator} onValueChange={handleOperatorChange}>
                <SelectTrigger className="w-full lg:w-48" id="operator-filter-2" disabled={isPending}>
                  <SelectValue placeholder="All operators" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All operators</SelectItem>
                  {uniqueOperators.map((operator) => (
                    <SelectItem key={operator} value={operator}>
                      {operator}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Restaurant Filter - Only show if not hidden */}
            {!hideRestaurantFilter && (
              <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:gap-2">
                <Label htmlFor="restaurant-filter-2" className="text-sm font-medium whitespace-nowrap">
                  Restaurant:
                </Label>
                <Select value={selectedRestaurant} onValueChange={handleRestaurantChange}>
                  <SelectTrigger className="w-full lg:w-56" id="restaurant-filter-2" disabled={isPending}>
                    <SelectValue placeholder="All restaurants" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All restaurants</SelectItem>
                    {uniqueRestaurants.map((restaurant) => (
                      <SelectItem key={restaurant} value={restaurant}>
                        {restaurant}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
            
            {/* Date Range Filter */}
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:gap-2">
              <Label className="text-sm font-medium whitespace-nowrap">
                Date Range:
              </Label>
              <div className="flex gap-2">
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className="w-full lg:w-36 justify-start text-left font-normal"
                      disabled={isPending}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {dateRange.from ? (
                        format(dateRange.from, "MMM dd, yyyy")
                      ) : (
                        <span>From date</span>
                      )}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={dateRange.from}
                      onSelect={(date: Date | undefined) => handleDateRangeChange('from', date)}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
                
                <Popover>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      className="w-full lg:w-36 justify-start text-left font-normal"
                      disabled={isPending}
                    >
                      <CalendarIcon className="mr-2 h-4 w-4" />
                      {dateRange.to ? (
                        format(dateRange.to, "MMM dd, yyyy")
                      ) : (
                        <span>To date</span>
                      )}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={dateRange.to}
                      onSelect={(date: Date | undefined) => handleDateRangeChange('to', date)}
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
                
                {(dateRange.from || dateRange.to) && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleClearDateRange}
                    className="px-2"
                    disabled={isPending}
                  >
                    Clear
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>
        
        <div className={`overflow-hidden rounded-lg border transition-all duration-300 ease-in-out ${
          isPending || isFiltering ? 'shadow-sm' : 'shadow-md'
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
            <TableBody className={`transition-opacity duration-300 ${isPending || isFiltering ? 'opacity-50' : 'opacity-100'}`}>
              {operatorTable.getRowModel().rows?.length ? (
                operatorTable.getRowModel().rows.map((row, index) => (
                  <SimpleRow 
                    key={row.id} 
                    row={row} 
                    index={index}
                    isPending={isPending || isFiltering}
                  />
                ))
              ) : (
                <TableRow>
                  <TableCell
                    colSpan={operatorColumns.length}
                    className="h-24 text-center"
                  >
                    No results.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
        
        <div className="flex items-center justify-between px-4">
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
      <TabsContent
        value="weekly-summary"
        className="flex flex-col gap-6 px-4 lg:px-6"
      >
        <TopPerformers data={filteredData} period="weekly" />
      </TabsContent>
      <TabsContent value="monthly-trends" className="flex flex-col gap-6 px-4 lg:px-6">
        <TopPerformers data={filteredData} period="monthly" />
      </TabsContent>
    </Tabs>
  )
}

const chartData = [
  { month: "January", desktop: 186, mobile: 80 },
  { month: "February", desktop: 305, mobile: 200 },
  { month: "March", desktop: 237, mobile: 120 },
  { month: "April", desktop: 73, mobile: 190 },
  { month: "May", desktop: 209, mobile: 130 },
  { month: "June", desktop: 214, mobile: 140 },
]

const chartConfig = {
  desktop: {
    label: "Desktop",
    color: "var(--primary)",
  },
  mobile: {
    label: "Mobile",
    color: "var(--primary)",
  },
} satisfies ChartConfig


