"use client"

import * as React from "react"
import { format } from "date-fns"
import {
  IconTrendingUp,
  IconTrendingDown,
  IconMinus,
  IconDownload,
  IconPrinter,
  IconX,
  IconLoader,
  IconAlertCircle,
  IconCheck,
  IconTarget,
  IconCash,
  IconShoppingCart,
  IconUsers,
} from "@tabler/icons-react"

import { useGetRunAnalytics, type RunAnalytics, type OperatorMetrics } from "@/hooks/getRunAnalytics"
import { TransactionsTable } from "@/components/transactions-table"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface RunAnalyticsReportProps {
  runId: string
  runDate?: string
  isOpen: boolean
  onClose: () => void
}

const MetricCard = ({ 
  title, 
  value, 
  subtitle, 
  icon: Icon, 
  trend, 
  trendValue,
  color = "gray" 
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: any
  trend?: "up" | "down" | "neutral"
  trendValue?: string
  color?: "blue" | "green" | "red" | "yellow" | "purple" | "gray"
}) => {
  const colorClasses = {
    blue: "text-blue-600 bg-blue-50 border-blue-200",
    green: "text-green-600 bg-green-50 border-green-200", 
    red: "text-red-600 bg-red-50 border-red-200",
    yellow: "text-yellow-600 bg-yellow-50 border-yellow-200",
    purple: "text-purple-600 bg-purple-50 border-purple-200",
    gray: "text-gray-900 bg-gray-50 border-gray-200"
  }

  const trendIcon = trend === "up" ? IconTrendingUp : trend === "down" ? IconTrendingDown : IconMinus
  const TrendIcon = trendIcon

  return (
    <Card className={`border ${colorClasses[color]}`}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className={`p-2 rounded-full ${colorClasses[color]}`}>
              <Icon className="h-5 w-5" />
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">{title}</p>
              <p className="text-2xl font-bold">{value}</p>
              {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
            </div>
          </div>
          {trend && trendValue && (
            <div className={`flex items-center space-x-1 ${
              trend === "up" ? "text-green-600" : trend === "down" ? "text-red-600" : "text-gray-600"
            }`}>
              <TrendIcon className="h-4 w-4" />
              <span className="text-sm font-medium">{trendValue}</span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

const PerformanceSection = ({ 
  title, 
  opportunities, 
  offers, 
  successes, 
  conversionRate, 
  revenue,
  color 
}: {
  title: string
  opportunities: number
  offers: number
  successes: number
  conversionRate: number
  revenue: number
  color: "blue" | "green" | "red" | "yellow" | "purple" | "gray"
}) => {
  const offerRate = opportunities > 0 ? (offers / opportunities) * 100 : 0
  const successRate = offers > 0 ? (successes / offers) * 100 : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <IconTarget className="h-5 w-5" />
          {title} Performance
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{opportunities}</div>
            <div className="text-sm text-muted-foreground">Opportunities</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{offers}</div>
            <div className="text-sm text-muted-foreground">Offers Made</div>
            <div className="text-xs text-muted-foreground">{offerRate.toFixed(1)}% rate</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">{successes}</div>
            <div className="text-sm text-muted-foreground">Successes</div>
            <div className="text-xs text-muted-foreground">{successRate.toFixed(1)}% rate</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-gray-900">${revenue.toFixed(2)}</div>
            <div className="text-sm text-muted-foreground">Revenue</div>
          </div>
        </div>
        
        {/* Progress bars */}
        <div className="space-y-2">
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Offer Rate</span>
              <span>{offerRate.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-gray-600 h-2 rounded-full transition-all duration-300" 
                style={{ width: `${Math.min(offerRate, 100)}%` }}
              />
            </div>
          </div>
          <div>
            <div className="flex justify-between text-sm mb-1">
              <span>Conversion Rate</span>
              <span>{conversionRate.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-gray-800 h-2 rounded-full transition-all duration-300" 
                style={{ width: `${Math.min(conversionRate, 100)}%` }}
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function RunAnalyticsReport({ runId, runDate, isOpen, onClose }: RunAnalyticsReportProps) {
  const { data: analytics, isLoading, isError, error } = useGetRunAnalytics(runId, isOpen)

  const handleExportPDF = () => {
    // Simple PDF export using window.print() with print styles
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;
    
    const reportContent = document.querySelector('.analytics-report-content');
    if (!reportContent) return;
    
    printWindow.document.write(`
      <html>
        <head>
          <title>Analytics Report - ${runId}</title>
          <style>
            body { 
              font-family: system-ui, -apple-system, sans-serif; 
              margin: 20px; 
              color: #333; 
              line-height: 1.4;
            }
            .header { 
              border-bottom: 2px solid #e5e7eb; 
              padding-bottom: 20px; 
              margin-bottom: 30px; 
            }
            .card { 
              border: 1px solid #e5e7eb; 
              border-radius: 8px; 
              padding: 20px; 
              margin-bottom: 20px; 
              break-inside: avoid;
            }
            .grid { 
              display: grid; 
              gap: 16px; 
            }
            .grid-cols-3 { 
              grid-template-columns: repeat(3, 1fr); 
            }
            .text-center { 
              text-align: center; 
            }
            .font-bold { 
              font-weight: bold; 
            }
            .text-2xl { 
              font-size: 1.5rem; 
            }
            .text-lg { 
              font-size: 1.125rem; 
            }
            .text-sm { 
              font-size: 0.875rem; 
            }
            .text-xs { 
              font-size: 0.75rem; 
            }
            .mb-2 { 
              margin-bottom: 8px; 
            }
            .mb-4 { 
              margin-bottom: 16px; 
            }
            .space-y-1 > * + * { 
              margin-top: 4px; 
            }
            .space-y-2 > * + * { 
              margin-top: 8px; 
            }
            .bg-blue-50 { 
              background-color: #eff6ff; 
            }
            .bg-green-50 { 
              background-color: #f0fdf4; 
            }
            .bg-purple-50 { 
              background-color: #faf5ff; 
            }
            .border-blue-200 { 
              border-color: #bfdbfe; 
            }
            .border-green-200 { 
              border-color: #bbf7d0; 
            }
            .border-purple-200 { 
              border-color: #e9d5ff; 
            }
            .text-blue-600 { 
              color: #2563eb; 
            }
            .text-green-600 { 
              color: #16a34a; 
            }
            .text-purple-600 { 
              color: #9333ea; 
            }
            .text-emerald-600 { 
              color: #059669; 
            }
            .text-muted-foreground { 
              color: #6b7280; 
            }
            @media print {
              body { margin: 0; font-size: 12px; }
              .card { break-inside: avoid; }
            }
          </style>
        </head>
        <body>
          <div class="header">
            <h1>Analytics Report</h1>
            <p>Run ID: ${runId}</p>
            <p>Date: ${runDate ? new Date(runDate).toLocaleDateString() : 'N/A'}</p>
            <p>Generated: ${new Date().toLocaleString()}</p>
          </div>
          ${reportContent.innerHTML}
        </body>
      </html>
    `);
    
    printWindow.document.close();
    printWindow.focus();
    
    // Wait for content to load, then print
    setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 1000);
  }

  const handlePrint = () => {
    window.print()
  }

  if (!isOpen) return null

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div>
              <DialogTitle className="text-2xl font-bold">
                Run Analytics Report
              </DialogTitle>
              <DialogDescription>
                {runDate && `Run Date: ${format(new Date(runDate), "MMMM dd, yyyy")}`}
                {analytics?.data?.location_name && ` • ${analytics.data.org_name} - ${analytics.data.location_name}`}
              </DialogDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={handlePrint}>
                <IconPrinter className="mr-2 h-4 w-4" />
                Print
              </Button>
              <Button variant="outline" size="sm" onClick={handleExportPDF}>
                <IconDownload className="mr-2 h-4 w-4" />
                Export PDF
              </Button>
            </div>
          </div>
        </DialogHeader>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <IconLoader className="h-8 w-8 animate-spin text-blue-600" />
            <span className="ml-2 text-lg">Loading analytics...</span>
          </div>
        )}

        {isError && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <IconAlertCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-2">Error Loading Analytics</h3>
              <p className="text-muted-foreground">{error?.message || "Failed to load analytics data"}</p>
            </div>
          </div>
        )}

        {analytics?.data && (
          <div className="space-y-6 print:space-y-4 analytics-report-content">
            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard
                title="Total Transactions"
                value={analytics.data.total_transactions.toLocaleString()}
                subtitle={`${analytics.data.completion_rate.toFixed(1)}% completion rate`}
                icon={IconShoppingCart}
                color="gray"
              />
              <MetricCard
                title="Total Revenue"
                value={`$${analytics.data.total_revenue.toFixed(2)}`}
                subtitle="From all initiatives"
                icon={IconCash}
                color="gray"
              />
              <MetricCard
                title="Overall Conversion"
                value={`${analytics.data.overall_conversion_rate.toFixed(1)}%`}
                subtitle={`${analytics.data.total_successes} of ${analytics.data.total_offers} offers`}
                icon={IconTarget}
                color="gray"
              />
              <MetricCard
                title="Avg Items Increase"
                value={analytics.data.avg_item_increase.toFixed(1)}
                subtitle={`From ${analytics.data.avg_items_initial.toFixed(1)} to ${analytics.data.avg_items_final.toFixed(1)}`}
                icon={IconTrendingUp}
                color="gray"
              />
            </div>

            <Separator />

            {/* Performance Sections */}
            <div className="space-y-6">
              <PerformanceSection
                title="Upselling"
                opportunities={analytics.data.upsell_opportunities}
                offers={analytics.data.upsell_offers}
                successes={analytics.data.upsell_successes}
                conversionRate={analytics.data.upsell_conversion_rate}
                revenue={analytics.data.upsell_revenue}
                color="gray"
              />

              <PerformanceSection
                title="Upsizing"
                opportunities={analytics.data.upsize_opportunities}
                offers={analytics.data.upsize_offers}
                successes={analytics.data.upsize_successes}
                conversionRate={analytics.data.upsize_conversion_rate}
                revenue={analytics.data.upsize_revenue}
                color="gray"
              />

              <PerformanceSection
                title="Add-ons"
                opportunities={analytics.data.addon_opportunities}
                offers={analytics.data.addon_offers}
                successes={analytics.data.addon_successes}
                conversionRate={analytics.data.addon_conversion_rate}
                revenue={analytics.data.addon_revenue}
                color="gray"
              />
            </div>

            {/* Operator Breakdown */}
            {analytics.data.detailed_analytics?.operator_analytics && (
              <div className="space-y-4">
                <h2 className="text-xl font-semibold flex items-center gap-2">
                  <IconUsers className="h-5 w-5" />
                  Operator Performance Breakdown
                </h2>
                {/* Get unique operator names from all categories */}
                {(() => {
                  const operatorNames = new Set<string>();
                  const operatorAnalytics = analytics.data.detailed_analytics.operator_analytics;
                  
                  // Collect all operator names from different categories
                  if (operatorAnalytics.upselling) {
                    Object.keys(operatorAnalytics.upselling).forEach(name => operatorNames.add(name));
                  }
                  if (operatorAnalytics.upsizing) {
                    Object.keys(operatorAnalytics.upsizing).forEach(name => operatorNames.add(name));
                  }
                  if (operatorAnalytics.addons) {
                    Object.keys(operatorAnalytics.addons).forEach(name => operatorNames.add(name));
                  }
                  
                  return Array.from(operatorNames).map(operatorName => {
                    const upsellingData = operatorAnalytics.upselling?.[operatorName];
                    const upsizingData = operatorAnalytics.upsizing?.[operatorName];
                    const addonsData = operatorAnalytics.addons?.[operatorName];
                    
                    return (
                  <Card key={operatorName}>
                    <CardHeader>
                      <CardTitle className="text-lg">{operatorName}</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-6">
                      {/* Operator Summary Cards */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="text-center p-4 bg-gray-50 rounded-lg border border-gray-200">
                          <div className="text-2xl font-bold text-gray-900">
                            {upsellingData?.total_successes || 0}
                          </div>
                          <div className="text-sm text-muted-foreground">Upselling Successes</div>
                          <div className="text-xs text-muted-foreground">
                            {(upsellingData?.conversion_rate || 0).toFixed(1)}% conversion
                          </div>
                        </div>
                        <div className="text-center p-4 bg-gray-50 rounded-lg border border-gray-200">
                          <div className="text-2xl font-bold text-gray-900">
                            {upsizingData?.total_successes || 0}
                          </div>
                          <div className="text-sm text-muted-foreground">Upsizing Successes</div>
                          <div className="text-xs text-muted-foreground">
                            {(upsizingData?.conversion_rate || 0).toFixed(1)}% conversion
                          </div>
                        </div>
                        <div className="text-center p-4 bg-gray-50 rounded-lg border border-gray-200">
                          <div className="text-2xl font-bold text-gray-900">
                            {addonsData?.total_successes || 0}
                          </div>
                          <div className="text-sm text-muted-foreground">Add-on Successes</div>
                          <div className="text-xs text-muted-foreground">
                            {(addonsData?.conversion_rate || 0).toFixed(1)}% conversion
                          </div>
                        </div>
                      </div>

                      {/* Operator Revenue Breakdown */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="text-center">
                          <div className="text-lg font-semibold text-gray-900">
                            ${(upsellingData?.total_revenue || 0).toFixed(2)}
                          </div>
                          <div className="text-sm text-muted-foreground">Upselling Revenue</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-semibold text-gray-900">
                            ${(upsizingData?.total_revenue || 0).toFixed(2)}
                          </div>
                          <div className="text-sm text-muted-foreground">Upsizing Revenue</div>
                        </div>
                        <div className="text-center">
                          <div className="text-lg font-semibold text-gray-900">
                            ${(addonsData?.total_revenue || 0).toFixed(2)}
                          </div>
                          <div className="text-sm text-muted-foreground">Add-on Revenue</div>
                        </div>
                      </div>

                      {/* Performance Metrics */}
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div>
                          <h5 className="font-medium mb-2">Upselling Performance</h5>
                          <div className="space-y-1">
                            <div>Opportunities: <span className="font-medium">{upsellingData?.total_opportunities || 0}</span></div>
                            <div>Offers: <span className="font-medium">{upsellingData?.total_offers || 0}</span></div>
                            <div>Offer Rate: <span className="font-medium">{(upsellingData?.offer_rate || 0).toFixed(1)}%</span></div>
                            <div>Success Rate: <span className="font-medium">{(upsellingData?.success_rate || 0).toFixed(1)}%</span></div>
                          </div>
                        </div>
                        <div>
                          <h5 className="font-medium mb-2">Upsizing Performance</h5>
                          <div className="space-y-1">
                            <div>Opportunities: <span className="font-medium">{upsizingData?.total_opportunities || 0}</span></div>
                            <div>Offers: <span className="font-medium">{upsizingData?.total_offers || 0}</span></div>
                            <div>Offer Rate: <span className="font-medium">{(upsizingData?.offer_rate || 0).toFixed(1)}%</span></div>
                            <div>Success Rate: <span className="font-medium">{(upsizingData?.success_rate || 0).toFixed(1)}%</span></div>
                          </div>
                        </div>
                        <div>
                          <h5 className="font-medium mb-2">Add-on Performance</h5>
                          <div className="space-y-1">
                            <div>Opportunities: <span className="font-medium">{addonsData?.total_opportunities || 0}</span></div>
                            <div>Offers: <span className="font-medium">{addonsData?.total_offers || 0}</span></div>
                            <div>Offer Rate: <span className="font-medium">{(addonsData?.offer_rate || 0).toFixed(1)}%</span></div>
                            <div>Success Rate: <span className="font-medium">{(addonsData?.success_rate || 0).toFixed(1)}%</span></div>
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                    );
                  });
                })()}
              </div>
            )}

            {/* Recommendations */}
            {analytics.data.detailed_analytics?.recommendations && analytics.data.detailed_analytics.recommendations.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <IconTarget className="h-5 w-5" />
                    AI Recommendations
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {analytics.data.detailed_analytics.recommendations.map((recommendation, index) => (
                      <li key={index} className="flex items-start gap-2">
                        <Badge variant="outline" className="mt-0.5 text-xs">
                          {index + 1}
                        </Badge>
                        <span className="text-sm">{recommendation}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Summary Section */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <IconCheck className="h-5 w-5" />
                  Performance Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div>
                    <h4 className="font-semibold mb-2">Opportunities</h4>
                    <div className="space-y-1 text-sm">
                      <div>Total: <span className="font-medium">{analytics.data.total_opportunities}</span></div>
                      <div>Upselling: <span className="font-medium">{analytics.data.upsell_opportunities}</span></div>
                      <div>Upsizing: <span className="font-medium">{analytics.data.upsize_opportunities}</span></div>
                      <div>Add-ons: <span className="font-medium">{analytics.data.addon_opportunities}</span></div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-2">Offers Made</h4>
                    <div className="space-y-1 text-sm">
                      <div>Total: <span className="font-medium">{analytics.data.total_offers}</span></div>
                      <div>Upselling: <span className="font-medium">{analytics.data.upsell_offers}</span></div>
                      <div>Upsizing: <span className="font-medium">{analytics.data.upsize_offers}</span></div>
                      <div>Add-ons: <span className="font-medium">{analytics.data.addon_offers}</span></div>
                    </div>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-2">Successes</h4>
                    <div className="space-y-1 text-sm">
                      <div>Total: <span className="font-medium">{analytics.data.total_successes}</span></div>
                      <div>Upselling: <span className="font-medium">{analytics.data.upsell_successes}</span></div>
                      <div>Upsizing: <span className="font-medium">{analytics.data.upsize_successes}</span></div>
                      <div>Add-ons: <span className="font-medium">{analytics.data.addon_successes}</span></div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Run Info */}
            <Card className="print:break-inside-avoid">
              <CardHeader>
                <CardTitle>Run Information</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Run ID:</span>
                    <div className="font-mono text-xs text-muted-foreground">{analytics.data.run_id}</div>
                  </div>
                  <div>
                    <span className="font-medium">Date:</span>
                    <div>{format(new Date(analytics.data.run_date), "MMMM dd, yyyy")}</div>
                  </div>
                  <div>
                    <span className="font-medium">Location:</span>
                    <div>{analytics.data.location_name}</div>
                  </div>
                  <div>
                    <span className="font-medium">Organization:</span>
                    <div>{analytics.data.org_name}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Transaction Details */}
            <TransactionsTable runId={analytics.data.run_id} pageSize={25} />
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
