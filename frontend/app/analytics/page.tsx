"use client"

import * as React from "react"
import { useState, useEffect } from "react"
import { RequireAuth } from "@/components/auth/RequireAuth"
import { AppLayout } from "@/components/app-layout"
import { AppSidebar } from "@/components/app-sidebar"
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { SiteHeader } from "@/components/site-header"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import {
  IconChartBar,
  IconLoader2,
  IconSearch,
  IconTrendingUp,
  IconUsers,
  IconShoppingCart,
  IconCurrencyDollar
} from "@tabler/icons-react"
import { toast } from "sonner"
import { 
  fetchLocations, 
  fetchRunsByLocation, 
  generateAnalytics, 
  fetchExistingAnalytics,
  formatCurrency,
  formatPercentage,
  formatDate,
  type Location,
  type Run,
  type StoreAnalytics
} from "@/lib/api"

// Components
function MetricCard({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  trend 
}: { 
  title: string
  value: string | number
  subtitle?: string
  icon: React.ComponentType<any>
  trend?: 'up' | 'down' | 'neutral'
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && (
          <p className="text-xs text-muted-foreground">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  )
}

function ItemBreakdownTable({ 
  items, 
  title 
}: { 
  items: Record<string, {
    opportunities: number
    offers: number
    successes: number
    revenue: number
    success_rate: number
    offer_rate: number
  }>
  title: string 
}) {
  const sortedItems = Object.entries(items)
    .sort(([,a], [,b]) => b.revenue - a.revenue)
    .slice(0, 10) // Top 10 items

  if (sortedItems.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">No data available</p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription>Top performing items by revenue</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {sortedItems.map(([itemName, stats]) => (
            <div key={itemName} className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex-1">
                <h4 className="font-medium">{itemName}</h4>
                <div className="flex gap-4 text-sm text-muted-foreground mt-1">
                  <span>{stats.opportunities} opportunities</span>
                  <span>{stats.offers} offers</span>
                  <span>{stats.successes} successes</span>
                </div>
              </div>
              <div className="text-right">
                <div className="font-semibold">${stats.revenue.toFixed(2)}</div>
                <div className="text-sm text-muted-foreground">
                  {stats.success_rate.toFixed(1)}% success
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

export default function AnalyticsPage() {
  const [locations, setLocations] = useState<Location[]>([])
  const [selectedLocationId, setSelectedLocationId] = useState<string>("")
  const [runs, setRuns] = useState<Run[]>([])
  const [selectedRunId, setSelectedRunId] = useState<string>("")
  const [analytics, setAnalytics] = useState<StoreAnalytics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)

  // Load locations on component mount
  useEffect(() => {
    const loadLocations = async () => {
      try {
        const locationData = await fetchLocations()
        setLocations(locationData)
      } catch (error) {
        console.error('Error loading locations:', error)
        toast.error('Failed to load locations')
      }
    }
    loadLocations()
  }, [])

  // Load runs when location is selected
  useEffect(() => {
    const loadRuns = async () => {
      if (!selectedLocationId) {
        setRuns([])
        return
      }

      setIsLoading(true)
      try {
        const runData = await fetchRunsByLocation(selectedLocationId)
        setRuns(runData)
      } catch (error) {
        console.error('Error loading runs:', error)
        toast.error('Failed to load runs for location')
      } finally {
        setIsLoading(false)
      }
    }
    loadRuns()
  }, [selectedLocationId])

  const handleGenerateAnalytics = async () => {
    if (!selectedRunId) {
      toast.error('Please select a run first')
      return
    }

    setIsGenerating(true)
    try {
      // First check if analytics already exist
      let analyticsData = await fetchExistingAnalytics(selectedRunId)
      
      if (analyticsData) {
        toast.success('Loaded existing analytics')
      } else {
        // Generate new analytics if none exist
        toast.info('Generating new analytics...')
        analyticsData = await generateAnalytics(selectedRunId)
        toast.success('Analytics generated successfully!')
      }
      
      setAnalytics(analyticsData)
    } catch (error) {
      console.error('Error generating analytics:', error)
      toast.error('Failed to generate analytics')
    } finally {
      setIsGenerating(false)
    }
  }

  const totalRevenue = analytics ? 
    analytics.upselling.summary.total_revenue + 
    analytics.upsizing.summary.total_revenue + 
    analytics.addons.summary.total_revenue : 0

  return (
    <RequireAuth>
      <SidebarProvider>
      <AppSidebar variant="inset" />
      <SidebarInset>
        <SiteHeader />
        <div className="flex flex-1 flex-col">
          <div className="@container/main flex flex-1 flex-col gap-6 p-4 lg:p-6">
            
            {/* Header */}
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <h1 className="text-3xl font-bold">Analytics Dashboard</h1>
                <p className="text-muted-foreground">
                  Generate comprehensive analytics for your locations
                </p>
              </div>
            </div>

            {/* Controls */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <IconSearch className="h-5 w-5" />
                  Generate Analytics
                </CardTitle>
                <CardDescription>
                  Select a location and run to generate comprehensive analytics
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="location-select">Location</Label>
                    <Select value={selectedLocationId} onValueChange={setSelectedLocationId}>
                      <SelectTrigger id="location-select">
                        <SelectValue placeholder="Select a location" />
                      </SelectTrigger>
                      <SelectContent>
                        {locations.map((location) => (
                          <SelectItem key={location.id} value={location.id}>
                            {location.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="run-select">Run</Label>
                    <Select 
                      value={selectedRunId} 
                      onValueChange={setSelectedRunId}
                      disabled={!selectedLocationId || isLoading}
                    >
                      <SelectTrigger id="run-select">
                        <SelectValue placeholder={
                          isLoading ? "Loading runs..." : "Select a run"
                        } />
                      </SelectTrigger>
                      <SelectContent>
                        {runs.map((run) => (
                          <SelectItem key={run.id} value={run.id}>
                            {run.name || run.id.slice(0, 8)} ({formatDate(run.created_at)})
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="flex items-end">
                    <Button 
                      onClick={handleGenerateAnalytics}
                      disabled={!selectedRunId || isGenerating}
                      className="w-full"
                    >
                      {isGenerating ? (
                        <>
                          <IconLoader2 className="mr-2 h-4 w-4 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <IconChartBar className="mr-2 h-4 w-4" />
                          Generate Analytics
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Analytics Display */}
            {analytics && (
              <div className="space-y-6">
                {/* Store Summary */}
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-2xl font-bold">{analytics.location_name}</h2>
                    <Badge variant="outline">
                      {analytics.summary.total_transactions} transactions
                    </Badge>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                    <MetricCard
                      title="Total Revenue"
                      value={formatCurrency(totalRevenue)}
                      subtitle="From upselling, upsizing & add-ons"
                      icon={IconCurrencyDollar}
                    />
                    <MetricCard
                      title="Completion Rate"
                      value={formatPercentage(analytics.summary.completion_rate)}
                      subtitle={`${analytics.summary.complete_transactions} completed`}
                      icon={IconTrendingUp}
                    />
                    <MetricCard
                      title="Avg Items Initial"
                      value={analytics.summary.avg_items_initial.toFixed(1)}
                      subtitle="Items per transaction"
                      icon={IconShoppingCart}
                    />
                    <MetricCard
                      title="Avg Items Final"
                      value={analytics.summary.avg_items_final.toFixed(1)}
                      subtitle={`+${analytics.summary.avg_item_increase.toFixed(1)} increase`}
                      icon={IconShoppingCart}
                    />
                  </div>
                </div>

                {/* Tabs for different analytics sections */}
                <Tabs defaultValue="store-overview" className="w-full">
                  <TabsList className="grid w-full grid-cols-4">
                    <TabsTrigger value="store-overview">Store Overview</TabsTrigger>
                    <TabsTrigger value="upselling">Upselling</TabsTrigger>
                    <TabsTrigger value="upsizing">Upsizing</TabsTrigger>
                    <TabsTrigger value="addons">Add-ons</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="store-overview" className="space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">Upselling Performance</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span>Conversion Rate:</span>
                              <span className="font-semibold">
                                {analytics.upselling.summary.conversion_rate.toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Revenue:</span>
                              <span className="font-semibold">
                                ${analytics.upselling.summary.total_revenue.toFixed(2)}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Successes:</span>
                              <span className="font-semibold">
                                {analytics.upselling.summary.total_successes}
                              </span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">Upsizing Performance</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span>Conversion Rate:</span>
                              <span className="font-semibold">
                                {analytics.upsizing.summary.conversion_rate.toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Revenue:</span>
                              <span className="font-semibold">
                                ${analytics.upsizing.summary.total_revenue.toFixed(2)}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Successes:</span>
                              <span className="font-semibold">
                                {analytics.upsizing.summary.total_successes}
                              </span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>

                      <Card>
                        <CardHeader>
                          <CardTitle className="text-lg">Add-ons Performance</CardTitle>
                        </CardHeader>
                        <CardContent>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span>Conversion Rate:</span>
                              <span className="font-semibold">
                                {analytics.addons.summary.conversion_rate.toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Revenue:</span>
                              <span className="font-semibold">
                                ${analytics.addons.summary.total_revenue.toFixed(2)}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span>Successes:</span>
                              <span className="font-semibold">
                                {analytics.addons.summary.total_successes}
                              </span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    </div>
                  </TabsContent>

                  <TabsContent value="upselling" className="space-y-4">
                    <ItemBreakdownTable
                      items={analytics.upselling.item_breakdown}
                      title="Upselling Item Performance"
                    />
                  </TabsContent>

                  <TabsContent value="upsizing" className="space-y-4">
                    <ItemBreakdownTable
                      items={analytics.upsizing.item_breakdown}
                      title="Upsizing Item Performance"
                    />
                  </TabsContent>

                  <TabsContent value="addons" className="space-y-4">
                    <ItemBreakdownTable
                      items={analytics.addons.item_breakdown}
                      title="Add-ons Item Performance"
                    />
                  </TabsContent>
                </Tabs>

                {/* Operator Analytics */}
                {Object.keys(analytics.operators).length > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-xl font-bold flex items-center gap-2">
                      <IconUsers className="h-5 w-5" />
                      Operator Performance
                    </h3>
                    
                    <div className="grid gap-4">
                      {Object.entries(analytics.operators).map(([operatorName, operatorData]) => (
                        <Card key={operatorName}>
                          <CardHeader>
                            <CardTitle>{operatorName}</CardTitle>
                          </CardHeader>
                          <CardContent>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              <div>
                                <h4 className="font-semibold mb-2">Upselling</h4>
                                <div className="space-y-1 text-sm">
                                  <div className="flex justify-between">
                                    <span>Rate:</span>
                                    <span>{operatorData.upselling.summary.conversion_rate.toFixed(1)}%</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>Revenue:</span>
                                    <span>${operatorData.upselling.summary.total_revenue.toFixed(2)}</span>
                                  </div>
                                </div>
                              </div>
                              <div>
                                <h4 className="font-semibold mb-2">Upsizing</h4>
                                <div className="space-y-1 text-sm">
                                  <div className="flex justify-between">
                                    <span>Rate:</span>
                                    <span>{operatorData.upsizing.summary.conversion_rate.toFixed(1)}%</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>Revenue:</span>
                                    <span>${operatorData.upsizing.summary.total_revenue.toFixed(2)}</span>
                                  </div>
                                </div>
                              </div>
                              <div>
                                <h4 className="font-semibold mb-2">Add-ons</h4>
                                <div className="space-y-1 text-sm">
                                  <div className="flex justify-between">
                                    <span>Rate:</span>
                                    <span>{operatorData.addons.summary.conversion_rate.toFixed(1)}%</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span>Revenue:</span>
                                    <span>${operatorData.addons.summary.total_revenue.toFixed(2)}</span>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
    </RequireAuth>
  )
}
