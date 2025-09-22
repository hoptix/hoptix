"use client"

import * as React from "react"
import { format } from "date-fns"
import { useParams, useRouter } from "next/navigation"
import {
  IconTrendingUp,
  IconTrendingDown,
  IconMinus,
  IconDownload,
  IconPrinter,
  IconArrowLeft,
  IconLoader,
  IconAlertCircle,
  IconCheck,
  IconTarget,
  IconCash,
  IconShoppingCart,
  IconUsers,
  IconEye,
} from "@tabler/icons-react"

import { useGetRunAnalytics, type RunAnalytics, type OperatorMetrics } from "@/hooks/getRunAnalytics"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

const MetricCard = ({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  trend, 
  trendValue,
  color = "neutral" 
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: any
  trend?: "up" | "down" | "neutral"
  trendValue?: string
  color?: "neutral" | "success" | "danger" | "primary"
}) => {
  const colorClasses = {
    neutral: "bg-white border-gray-200 hover:border-gray-300",
    success: "bg-white border-green-200 hover:border-green-300",
    danger: "bg-white border-red-200 hover:border-red-300", 
    primary: "bg-white border-blue-200 hover:border-blue-300"
  }

  const iconClasses = {
    neutral: "bg-gray-100 text-gray-600",
    success: "bg-green-100 text-green-600",
    danger: "bg-red-100 text-red-600",
    primary: "bg-blue-100 text-blue-600"
  }

  const trendIcon = trend === "up" ? IconTrendingUp : trend === "down" ? IconTrendingDown : IconMinus
  const TrendIcon = trendIcon

  return (
    <Card className={`transition-all duration-200 shadow-sm hover:shadow-md ${colorClasses[color]}`}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-4">
            <div className={`p-3 rounded-xl ${iconClasses[color]}`}>
              <Icon className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600 mb-1">{title}</p>
              <p className="text-3xl font-bold text-gray-900 mb-1">{value}</p>
              {subtitle && <p className="text-sm text-gray-500">{subtitle}</p>}
            </div>
          </div>
          {trend && trendValue && (
            <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-sm font-medium ${
              trend === "up" ? "bg-green-100 text-green-700" : 
              trend === "down" ? "bg-red-100 text-red-700" : 
              "bg-gray-100 text-gray-700"
            }`}>
              <TrendIcon className="h-4 w-4" />
              <span>{trendValue}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function AnalyticsReportPage() {
  const params = useParams()
  const router = useRouter()
  const runId = params.runId as string

  const { data: analytics, isLoading, isError, error } = useGetRunAnalytics(runId)

  const handleViewTransactions = () => {
    router.push(`/reports/${runId}/transactions`)
  }

  const handleGoBack = () => {
    router.back()
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <IconLoader className="h-8 w-8 animate-spin mx-auto mb-4" />
          <h2 className="text-xl font-semibold">Loading Analytics...</h2>
          <p className="text-muted-foreground">Please wait while we fetch the run data.</p>
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <IconAlertCircle className="h-8 w-8 text-red-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-red-600">Error Loading Analytics</h2>
          <p className="text-muted-foreground">{error?.message || 'Failed to load analytics data'}</p>
          <Button onClick={handleGoBack} className="mt-4">
            <IconArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </div>
      </div>
    )
  }

  if (!analytics?.success || !analytics?.data) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <IconAlertCircle className="h-8 w-8 text-yellow-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold">No Data Available</h2>
          <p className="text-muted-foreground">No analytics data found for this run.</p>
          <Button onClick={handleGoBack} className="mt-4">
            <IconArrowLeft className="h-4 w-4 mr-2" />
            Go Back
          </Button>
        </div>
      </div>
    )
  }

  const data = analytics.data

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-6 py-8 max-w-7xl">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <Button variant="outline" onClick={handleGoBack} className="border-gray-300 hover:border-gray-400">
                <IconArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
              <div className="border-l border-gray-300 pl-6">
                <h1 className="text-4xl font-bold text-gray-900 mb-2">Analytics Report</h1>
                <div className="flex items-center space-x-3 text-gray-600">
                  <span className="text-lg font-medium">
                    {format(new Date(data.run_date), "MMMM dd, yyyy")}
                  </span>
                  <span className="text-gray-400">•</span>
                  <span className="text-lg">{data.location_name}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <Button variant="outline" onClick={handleViewTransactions} className="border-gray-300 hover:border-gray-400">
                <IconEye className="h-4 w-4 mr-2" />
                View Raw Transactions
              </Button>
              <Button variant="outline" onClick={() => window.print()} className="border-gray-300 hover:border-gray-400">
                <IconPrinter className="h-4 w-4 mr-2" />
                Print Report
              </Button>
            </div>
          </div>
        </div>

        <div className="space-y-8">
          {/* Key Metrics Section */}
          <section>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Key Performance Metrics</h2>
              <p className="text-gray-600">Overview of transaction performance and revenue impact</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard
                title="Total Transactions"
                value={data.total_transactions}
                subtitle="Orders processed"
                icon={IconShoppingCart}
                color="neutral"
              />
              <MetricCard
                title="Total Revenue"
                value={`$${data.total_revenue?.toFixed(2) || '0.00'}`}
                subtitle="Generated"
                icon={IconCash}
                color="success"
              />
              <MetricCard
                title="Success Rate"
                value={`${((data.total_successes / Math.max(data.total_opportunities, 1)) * 100).toFixed(1)}%`}
                subtitle="Overall performance"
                icon={IconTarget}
                color="primary"
              />
              <MetricCard
                title="Total Opportunities"
                value={data.total_opportunities}
                subtitle="Identified"
                icon={IconCheck}
                color="neutral"
              />
            </div>
          </section>

          {/* Performance Breakdown Section */}
          <section>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Performance Breakdown</h2>
              <p className="text-gray-600">Detailed analysis of upselling, upsizing, and add-on performance</p>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Upselling */}
              <Card className="bg-white border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200">
                <CardHeader className="pb-4">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-green-100 rounded-lg">
                      <IconTrendingUp className="h-5 w-5 text-green-600" />
                    </div>
                    <CardTitle className="text-lg font-semibold text-gray-900">Upselling</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900">{data.upsell_opportunities}</div>
                      <div className="text-sm text-gray-600">Opportunities</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900">{data.upsell_offers}</div>
                      <div className="text-sm text-gray-600">Offers</div>
                    </div>
                  </div>
                  <div className="border-t border-gray-200 pt-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">Success Rate</span>
                      <Badge className={`${
                        data.upsell_opportunities > 0 && ((data.upsell_successes / data.upsell_opportunities) * 100) >= 50
                          ? 'bg-green-100 text-green-800 hover:bg-green-200'
                          : 'bg-red-100 text-red-800 hover:bg-red-200'
                      }`}>
                        {data.upsell_opportunities > 0 
                          ? `${((data.upsell_successes / data.upsell_opportunities) * 100).toFixed(1)}%`
                          : '0%'
                        }
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-gray-700">Revenue Impact</span>
                      <span className="font-bold text-green-600">${data.upsell_revenue?.toFixed(2) || '0.00'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Upsizing */}
              <Card className="bg-white border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200">
                <CardHeader className="pb-4">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-blue-100 rounded-lg">
                      <IconTarget className="h-5 w-5 text-blue-600" />
                    </div>
                    <CardTitle className="text-lg font-semibold text-gray-900">Upsizing</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900">{data.upsize_opportunities}</div>
                      <div className="text-sm text-gray-600">Opportunities</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900">{data.upsize_offers}</div>
                      <div className="text-sm text-gray-600">Offers</div>
                    </div>
                  </div>
                  <div className="border-t border-gray-200 pt-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">Success Rate</span>
                      <Badge className={`${
                        data.upsize_opportunities > 0 && ((data.upsize_successes / data.upsize_opportunities) * 100) >= 50
                          ? 'bg-green-100 text-green-800 hover:bg-green-200'
                          : 'bg-red-100 text-red-800 hover:bg-red-200'
                      }`}>
                        {data.upsize_opportunities > 0 
                          ? `${((data.upsize_successes / data.upsize_opportunities) * 100).toFixed(1)}%`
                          : '0%'
                        }
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-gray-700">Revenue Impact</span>
                      <span className="font-bold text-blue-600">${data.upsize_revenue?.toFixed(2) || '0.00'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Add-ons */}
              <Card className="bg-white border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200">
                <CardHeader className="pb-4">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-purple-100 rounded-lg">
                      <IconShoppingCart className="h-5 w-5 text-purple-600" />
                    </div>
                    <CardTitle className="text-lg font-semibold text-gray-900">Add-ons</CardTitle>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900">{data.addon_opportunities}</div>
                      <div className="text-sm text-gray-600">Opportunities</div>
                    </div>
                    <div className="text-center p-3 bg-gray-50 rounded-lg">
                      <div className="text-2xl font-bold text-gray-900">{data.addon_offers}</div>
                      <div className="text-sm text-gray-600">Offers</div>
                    </div>
                  </div>
                  <div className="border-t border-gray-200 pt-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm font-medium text-gray-700">Success Rate</span>
                      <Badge className={`${
                        data.addon_opportunities > 0 && ((data.addon_successes / data.addon_opportunities) * 100) >= 50
                          ? 'bg-green-100 text-green-800 hover:bg-green-200'
                          : 'bg-red-100 text-red-800 hover:bg-red-200'
                      }`}>
                        {data.addon_opportunities > 0 
                          ? `${((data.addon_successes / data.addon_opportunities) * 100).toFixed(1)}%`
                          : '0%'
                        }
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm font-medium text-gray-700">Revenue Impact</span>
                      <span className="font-bold text-purple-600">${data.addon_revenue?.toFixed(2) || '0.00'}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>

          {/* Summary Section */}
          <section>
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Summary & Details</h2>
              <p className="text-gray-600">Comprehensive overview and run information</p>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Performance Summary */}
              <Card className="bg-white border border-gray-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold text-gray-900">Performance Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-6">
                    <div>
                      <h4 className="font-semibold text-gray-800 mb-3 text-sm uppercase tracking-wide">Opportunities</h4>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="bg-gray-50 p-3 rounded-lg">
                          <div className="text-lg font-bold text-gray-900">{data.total_opportunities}</div>
                          <div className="text-xs text-gray-600">Total</div>
                        </div>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-600">Upselling:</span>
                            <span className="font-medium text-gray-900">{data.upsell_opportunities}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600">Upsizing:</span>
                            <span className="font-medium text-gray-900">{data.upsize_opportunities}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-600">Add-ons:</span>
                            <span className="font-medium text-gray-900">{data.addon_opportunities}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="border-t border-gray-200 pt-4">
                      <h4 className="font-semibold text-gray-800 mb-3 text-sm uppercase tracking-wide">Success Rate</h4>
                      <div className="text-center">
                        <div className="text-3xl font-bold text-gray-900 mb-1">
                          {((data.total_successes / Math.max(data.total_opportunities, 1)) * 100).toFixed(1)}%
                        </div>
                        <div className="text-sm text-gray-600">
                          {data.total_successes} of {data.total_opportunities} opportunities converted
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Run Information */}
              <Card className="bg-white border border-gray-200 shadow-sm">
                <CardHeader>
                  <CardTitle className="text-lg font-semibold text-gray-900">Run Information</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="grid grid-cols-1 gap-4">
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <div className="text-sm font-medium text-gray-700 mb-1">Run ID</div>
                        <div className="font-mono text-xs text-gray-600 break-all">{data.run_id}</div>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <div className="text-sm font-medium text-gray-700 mb-1">Date</div>
                          <div className="text-sm text-gray-900">{format(new Date(data.run_date), "MMM dd, yyyy")}</div>
                        </div>
                        <div>
                          <div className="text-sm font-medium text-gray-700 mb-1">Transactions</div>
                          <div className="text-sm text-gray-900">{data.total_transactions}</div>
                        </div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-700 mb-1">Location</div>
                        <div className="text-sm text-gray-900">{data.location_name}</div>
                      </div>
                      <div>
                        <div className="text-sm font-medium text-gray-700 mb-1">Organization</div>
                        <div className="text-sm text-gray-900">{data.org_name}</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </section>

          {/* Operator Performance Section */}
          {data.detailed_analytics?.operator_analytics && (
            <section>
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Operator Performance</h2>
                <p className="text-gray-600">Individual performance metrics by team member</p>
              </div>
              {/* Get all unique operator names from the three categories */}
              {(() => {
                const operators = new Set<string>();
                if (data.detailed_analytics.operator_analytics.upselling) {
                  Object.keys(data.detailed_analytics.operator_analytics.upselling).forEach(op => operators.add(op));
                }
                if (data.detailed_analytics.operator_analytics.upsizing) {
                  Object.keys(data.detailed_analytics.operator_analytics.upsizing).forEach(op => operators.add(op));
                }
                if (data.detailed_analytics.operator_analytics.addons) {
                  Object.keys(data.detailed_analytics.operator_analytics.addons).forEach(op => operators.add(op));
                }
                
                return Array.from(operators).map(operatorName => (
                  <div key={operatorName} className="mb-8">
                    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
                      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-4 border-b border-gray-200">
                        <div className="flex items-center space-x-3">
                          <div className="p-2 bg-blue-100 rounded-full">
                            <IconUsers className="h-5 w-5 text-blue-600" />
                          </div>
                          <h3 className="text-xl font-semibold text-gray-900">{operatorName}</h3>
                        </div>
                      </div>
                      
                      <div className="p-6">
                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                          {/* Operator Upselling */}
                          <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                            <div className="flex items-center justify-between mb-4">
                              <div className="flex items-center space-x-2">
                                <div className="p-1 bg-green-100 rounded-lg">
                                  <IconTrendingUp className="h-4 w-4 text-green-600" />
                                </div>
                                <h4 className="font-semibold text-gray-900">Upselling</h4>
                              </div>
                              <Badge className={`${
                                (data.detailed_analytics.operator_analytics.upselling?.[operatorName]?.success_rate || 0) >= 50
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {data.detailed_analytics.operator_analytics.upselling?.[operatorName]?.success_rate?.toFixed(1) || '0'}%
                              </Badge>
                            </div>
                            <div className="space-y-3">
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Offers:</span>
                                <span className="font-medium text-gray-900">
                                  {data.detailed_analytics.operator_analytics.upselling?.[operatorName]?.total_offers || 0}
                                </span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Successes:</span>
                                <span className="font-medium text-green-600">
                                  {data.detailed_analytics.operator_analytics.upselling?.[operatorName]?.total_successes || 0}
                                </span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Revenue:</span>
                                <span className="font-semibold text-green-600">
                                  ${data.detailed_analytics.operator_analytics.upselling?.[operatorName]?.total_revenue?.toFixed(2) || '0.00'}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Operator Upsizing */}
                          <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                            <div className="flex items-center justify-between mb-4">
                              <div className="flex items-center space-x-2">
                                <div className="p-1 bg-blue-100 rounded-lg">
                                  <IconTarget className="h-4 w-4 text-blue-600" />
                                </div>
                                <h4 className="font-semibold text-gray-900">Upsizing</h4>
                              </div>
                              <Badge className={`${
                                (data.detailed_analytics.operator_analytics.upsizing?.[operatorName]?.success_rate || 0) >= 50
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {data.detailed_analytics.operator_analytics.upsizing?.[operatorName]?.success_rate?.toFixed(1) || '0'}%
                              </Badge>
                            </div>
                            <div className="space-y-3">
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Offers:</span>
                                <span className="font-medium text-gray-900">
                                  {data.detailed_analytics.operator_analytics.upsizing?.[operatorName]?.total_offers || 0}
                                </span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Successes:</span>
                                <span className="font-medium text-blue-600">
                                  {data.detailed_analytics.operator_analytics.upsizing?.[operatorName]?.total_successes || 0}
                                </span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Revenue:</span>
                                <span className="font-semibold text-blue-600">
                                  ${data.detailed_analytics.operator_analytics.upsizing?.[operatorName]?.total_revenue?.toFixed(2) || '0.00'}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Operator Add-ons */}
                          <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                            <div className="flex items-center justify-between mb-4">
                              <div className="flex items-center space-x-2">
                                <div className="p-1 bg-purple-100 rounded-lg">
                                  <IconShoppingCart className="h-4 w-4 text-purple-600" />
                                </div>
                                <h4 className="font-semibold text-gray-900">Add-ons</h4>
                              </div>
                              <Badge className={`${
                                (data.detailed_analytics.operator_analytics.addons?.[operatorName]?.success_rate || 0) >= 50
                                  ? 'bg-green-100 text-green-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {data.detailed_analytics.operator_analytics.addons?.[operatorName]?.success_rate?.toFixed(1) || '0'}%
                              </Badge>
                            </div>
                            <div className="space-y-3">
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Offers:</span>
                                <span className="font-medium text-gray-900">
                                  {data.detailed_analytics.operator_analytics.addons?.[operatorName]?.total_offers || 0}
                                </span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Successes:</span>
                                <span className="font-medium text-purple-600">
                                  {data.detailed_analytics.operator_analytics.addons?.[operatorName]?.total_successes || 0}
                                </span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Revenue:</span>
                                <span className="font-semibold text-purple-600">
                                  ${data.detailed_analytics.operator_analytics.addons?.[operatorName]?.total_revenue?.toFixed(2) || '0.00'}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                ));
              })()}
            </section>
          )}

          {/* Item Performance Section */}
          {data.detailed_analytics && (
            <section>
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">Item Performance Breakdown</h2>
                <p className="text-gray-600">Top performing items across all categories</p>
              </div>
              
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Upselling Items */}
                {data.detailed_analytics.upselling?.by_item && (
                  <Card className="bg-white border border-gray-200 shadow-sm">
                    <CardHeader className="pb-4">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-green-100 rounded-lg">
                          <IconTrendingUp className="h-5 w-5 text-green-600" />
                        </div>
                        <CardTitle className="text-lg font-semibold text-gray-900">Top Upselling Items</CardTitle>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3 max-h-80 overflow-y-auto">
                        {Object.entries(data.detailed_analytics.upselling.by_item)
                          .filter(([_, itemData]: [string, any]) => itemData.successes > 0)
                          .sort(([_, a]: [string, any], [__, b]: [string, any]) => b.successes - a.successes)
                          .slice(0, 8)
                          .map(([itemName, itemData]: [string, any]) => (
                            <div key={itemName} className="border border-gray-200 rounded-lg p-3 hover:bg-green-50 transition-colors">
                              <div className="flex items-center justify-between">
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium text-sm text-gray-900 truncate">{itemName}</div>
                                  <div className="text-xs text-gray-500 mt-1">
                                    {itemData.offers} offers • {itemData.opportunities} opportunities
                                  </div>
                                </div>
                                <div className="text-right ml-3">
                                  <div className="font-bold text-green-600 text-sm">{itemData.successes}</div>
                                  <div className="text-xs text-gray-500">
                                    {itemData.success_rate?.toFixed(1)}%
                                  </div>
                                  <div className="text-xs font-medium text-green-600">
                                    ${itemData.revenue?.toFixed(2)}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Upsizing Items */}
                {data.detailed_analytics.upsizing?.by_item && (
                  <Card className="bg-white border border-gray-200 shadow-sm">
                    <CardHeader className="pb-4">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                          <IconTarget className="h-5 w-5 text-blue-600" />
                        </div>
                        <CardTitle className="text-lg font-semibold text-gray-900">Top Upsizing Items</CardTitle>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3 max-h-80 overflow-y-auto">
                        {Object.entries(data.detailed_analytics.upsizing.by_item)
                          .filter(([_, itemData]: [string, any]) => itemData.successes > 0)
                          .sort(([_, a]: [string, any], [__, b]: [string, any]) => b.successes - a.successes)
                          .slice(0, 8)
                          .map(([itemName, itemData]: [string, any]) => (
                            <div key={itemName} className="border border-gray-200 rounded-lg p-3 hover:bg-blue-50 transition-colors">
                              <div className="flex items-center justify-between">
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium text-sm text-gray-900 truncate">{itemName}</div>
                                  <div className="text-xs text-gray-500 mt-1">
                                    {itemData.offers} offers • {itemData.opportunities} opportunities
                                  </div>
                                </div>
                                <div className="text-right ml-3">
                                  <div className="font-bold text-blue-600 text-sm">{itemData.successes}</div>
                                  <div className="text-xs text-gray-500">
                                    {itemData.success_rate?.toFixed(1)}%
                                  </div>
                                  <div className="text-xs font-medium text-blue-600">
                                    ${itemData.revenue?.toFixed(2)}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                      </div>
                    </CardContent>
                  </Card>
                )}

                {/* Add-on Items */}
                {data.detailed_analytics.addons?.by_item && (
                  <Card className="bg-white border border-gray-200 shadow-sm">
                    <CardHeader className="pb-4">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-purple-100 rounded-lg">
                          <IconShoppingCart className="h-5 w-5 text-purple-600" />
                        </div>
                        <CardTitle className="text-lg font-semibold text-gray-900">Top Add-on Items</CardTitle>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3 max-h-80 overflow-y-auto">
                        {Object.entries(data.detailed_analytics.addons.by_item)
                          .filter(([_, itemData]: [string, any]) => itemData.successes > 0)
                          .sort(([_, a]: [string, any], [__, b]: [string, any]) => b.successes - a.successes)
                          .slice(0, 8)
                          .map(([itemName, itemData]: [string, any]) => (
                            <div key={itemName} className="border border-gray-200 rounded-lg p-3 hover:bg-purple-50 transition-colors">
                              <div className="flex items-center justify-between">
                                <div className="flex-1 min-w-0">
                                  <div className="font-medium text-sm text-gray-900 truncate">{itemName}</div>
                                  <div className="text-xs text-gray-500 mt-1">
                                    {itemData.offers} offers • {itemData.opportunities} opportunities
                                  </div>
                                </div>
                                <div className="text-right ml-3">
                                  <div className="font-bold text-purple-600 text-sm">{itemData.successes}</div>
                                  <div className="text-xs text-gray-500">
                                    {itemData.success_rate?.toFixed(1)}%
                                  </div>
                                  <div className="text-xs font-medium text-purple-600">
                                    ${itemData.revenue?.toFixed(2)}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
