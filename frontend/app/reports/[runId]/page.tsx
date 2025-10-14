"use client"

import * as React from "react"
import { format } from "date-fns"
import { useParams, useRouter } from "next/navigation"
import { RequireAuth } from "@/components/auth/RequireAuth"
import { useState } from "react"
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
  IconChevronDown,
  IconChevronRight,
} from "@tabler/icons-react"

import { useGetRunAnalytics, useGetWorkerAnalytics, type RunAnalytics, type OperatorMetrics, type ItemAnalytics, type SizeMetrics, type DetailedAnalytics, type WorkerAnalytics } from "@/hooks/getRunAnalytics"
import { useRunAIFeedback } from "@/hooks/useRunAIFeedback"
import { RunAIFeedbackDisplay } from "@/components/run-ai-feedback-display"
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

// Component for displaying size transition data
const SizeTransitionCard = ({ itemId, itemName, transitions }: { itemId: string, itemName: string, transitions: ItemAnalytics['transitions'] }) => {
  const totalTransitions = transitions["1_to_2"] + transitions["1_to_3"] + transitions["2_to_3"];
  
  if (totalTransitions === 0) {
    return null; // Don't show items with no transitions
  }

  const transitionData = [
    { key: "1_to_2", label: "Small → Medium", value: transitions["1_to_2"], color: "blue" },
    { key: "1_to_3", label: "Small → Large", value: transitions["1_to_3"], color: "green" },
    { key: "2_to_3", label: "Medium → Large", value: transitions["2_to_3"], color: "purple" }
  ].filter(item => item.value > 0);

  if (transitionData.length === 0) return null;

  return (
    <Card className="bg-white border border-gray-200 shadow-sm hover:shadow-md transition-all duration-200">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-xl font-bold text-gray-900">{itemName}</CardTitle>
            <p className="text-sm text-gray-600 mt-1">Size upgrade transitions</p>
          </div>
          <div className="text-right">
            <div className="text-2xl font-bold text-gray-900">{totalTransitions}</div>
            <div className="text-xs text-gray-500 uppercase tracking-wide">Total Upgrades</div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {transitionData.map(({ key, label, value, color }) => {
            const percentage = totalTransitions > 0 ? (value / totalTransitions * 100) : 0;
            const colorClasses = {
              blue: "bg-blue-50 border-blue-200 text-blue-700",
              green: "bg-green-50 border-green-200 text-green-700", 
              purple: "bg-purple-50 border-purple-200 text-purple-700"
            };
            
            return (
              <div key={key} className={`p-4 rounded-lg border ${colorClasses[color as keyof typeof colorClasses]}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="font-semibold">{label}</div>
                  <div className="text-2xl font-bold">{value}</div>
                </div>
                <div className="w-full bg-white/50 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full transition-all duration-300 ${
                      color === 'blue' ? 'bg-blue-500' : 
                      color === 'green' ? 'bg-green-500' : 'bg-purple-500'
                    }`}
                    style={{ width: `${percentage}%` }}
                  ></div>
                </div>
                <div className="text-xs mt-1 opacity-75">{percentage.toFixed(1)}% of total upgrades</div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};

// Component for displaying items suggestively sold
const ItemsSuggestivelySoldTable = ({ items }: { items: [string, ItemAnalytics][] }) => {
  const [page, setPage] = useState(1);
  const pageSize = 10;
  const [sortKey, setSortKey] = useState<
    'name' | 'upsellBase' | 'upsellOffered' | 'upsellSold' | 'upsizeBase' | 'upsizeOffered' | 'upsizeSold' | 'addonBase' | 'addonOffered' | 'addonSold'
  >('name');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  const [filterQuery, setFilterQuery] = useState<string>('');
  const [expandedItems, setExpandedItems] = useState<Set<string>>(new Set());

  const getItemTotals = (itemData: ItemAnalytics) => {
    const sizeEntries = Object.entries(itemData.sizes);
    return sizeEntries.reduce((acc, [_, metrics]) => ({
      upsell: {
        candidates: (acc.upsell.candidates || 0) + (metrics.upsell_candidates || 0),
        offered: (acc.upsell.offered || 0) + (metrics.upsell_offered || 0),
        sold: (acc.upsell.sold || 0) + (metrics.upsell_base_sold || 0)
      },
      upsize: {
        candidates: (acc.upsize.candidates || 0) + (metrics.upsize_candidates || 0),
        offered: (acc.upsize.offered || 0) + (metrics.upsize_offered || 0),
        sold: (acc.upsize.sold || 0) + (metrics.upsize_base_sold || 0)
      },
      addon: {
        candidates: (acc.addon.candidates || 0) + (metrics.addon_candidates || 0),
        offered: (acc.addon.offered || 0) + (metrics.addon_offered || 0),
        sold: (acc.addon.sold || 0) + (metrics.addon_base_sold || 0)
      }
    }), {
      upsell: { candidates: 0, offered: 0, sold: 0 },
      upsize: { candidates: 0, offered: 0, sold: 0 },
      addon: { candidates: 0, offered: 0, sold: 0 }
    });
  };

  const filteredItems = items.filter(([_, itemData]) => {
    if (!filterQuery.trim()) return true;
    return itemData.name.toLowerCase().includes(filterQuery.trim().toLowerCase());
  });

  const withComputed = filteredItems.map(([itemId, itemData]) => {
    const totals = getItemTotals(itemData);
    const totalOffers = (totals.upsell.offered || 0) + (totals.upsize.offered || 0) + (totals.addon.offered || 0);
    const totalOpportunities = (totals.upsell.candidates || 0) + (totals.upsize.candidates || 0) + (totals.addon.candidates || 0);
    const totalConversions = (totals.upsell.sold || 0) + (totals.upsize.sold || 0) + (totals.addon.sold || 0);
    return { itemId, itemData, totals, totalOffers, totalOpportunities, totalConversions };
  });

  const sorted = [...withComputed]
    .filter((x) => (x.totalOffers || 0) > 0)
    .sort((a, b) => (b.totalOffers || 0) - (a.totalOffers || 0));

  const totalPages = Math.max(1, Math.ceil(sorted.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const start = (currentPage - 1) * pageSize;
  const pageItems = sorted.slice(start, start + pageSize);

  const setSort = (key: typeof sortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
    setPage(1);
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
      {/* Controls and status */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between px-4 py-3 bg-gray-50 border-b border-gray-200 space-y-3 md:space-y-0">
        <div className="flex items-center space-x-2">
          <input
            type="text"
            value={filterQuery}
            onChange={(e) => { setFilterQuery(e.target.value); setPage(1); }}
            placeholder="Filter items by name..."
            className="w-full md:w-72 px-3 py-2 text-sm border border-gray-300 rounded"
          />
        </div>
        <div className="text-xs text-gray-600">
          <span className="mr-3">Sorting by: <span className="font-medium">{
            sortKey === 'name' ? 'Item' :
            sortKey === 'upsellBase' ? 'Upsell Base' :
            sortKey === 'upsellOffered' ? 'Upsell Offered' :
            sortKey === 'upsellSold' ? 'Upsell Sold' :
            sortKey === 'upsizeBase' ? 'Upsize Base' :
            sortKey === 'upsizeOffered' ? 'Upsize Offered' :
            sortKey === 'upsizeSold' ? 'Upsize Sold' :
            sortKey === 'addonBase' ? 'Add-on Base' :
            sortKey === 'addonOffered' ? 'Add-on Offered' :
            'Add-on Sold'
          } ({sortDir.toUpperCase()})</span></span>
          <span>Filter: <span className="font-medium">{filterQuery.trim() ? `name contains "${filterQuery.trim()}"` : 'None'}</span></span>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-200">
            <tr>
              <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                <button onClick={() => setSort('name')} className="flex items-center space-x-1">
                  <span>Item</span>
                  <span className="text-gray-400 text-[10px]">{sortKey==='name' ? (sortDir==='asc'?'▲':'▼') : ''}</span>
                </button>
              </th>
              <th className="px-6 py-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Offers</th>
              <th className="px-6 py-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Opportunities</th>
              <th className="px-6 py-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Conversions</th>
              <th className="px-6 py-4 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {pageItems.map(({ itemId, itemData, totals }) => {
              const isExpanded = expandedItems.has(itemId);
              const totalOffers = totals.upsell.offered + totals.upsize.offered + totals.addon.offered;
              const totalOpportunities = (totals.upsell.candidates || 0) + (totals.upsize.candidates || 0) + (totals.addon.candidates || 0);
              const totalConversions = totals.upsell.sold + totals.upsize.sold + totals.addon.sold;

              return (
                <React.Fragment key={itemId}>
                  <tr className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <button
                          onClick={() => {
                            const next = new Set(expandedItems);
                            next.has(itemId) ? next.delete(itemId) : next.add(itemId);
                            setExpandedItems(next);
                          }}
                          className="flex items-center space-x-3 text-left hover:text-blue-600 transition-colors"
                        >
                          {isExpanded ? (
                            <IconChevronDown className="h-4 w-4 text-gray-400" />
                          ) : (
                            <IconChevronRight className="h-4 w-4 text-gray-400" />
                          )}
                          <div>
                            <div className="text-sm font-medium text-gray-900">{itemData.name}</div>
                            <div className="text-xs text-gray-500">Click to expand details</div>
                          </div>
                        </button>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center"><div className="text-sm font-semibold text-gray-900">{totalOffers}</div></td>
                    <td className="px-6 py-4 whitespace-nowrap text-center"><div className="text-sm font-semibold text-gray-900">{totalOpportunities}</div></td>
                    <td className="px-6 py-4 whitespace-nowrap text-center"><div className="text-sm font-semibold text-gray-900">{totalConversions}</div></td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <button
                        onClick={() => {
                          const next = new Set(expandedItems);
                          next.has(itemId) ? next.delete(itemId) : next.add(itemId);
                          setExpandedItems(next);
                        }}
                        className="text-blue-600 hover:text-blue-800 text-sm font-medium transition-colors"
                      >
                        {isExpanded ? 'Collapse' : 'Expand'}
                      </button>
                    </td>
                  </tr>

                  {isExpanded && (
                    <tr>
                      <td colSpan={5} className="px-6 py-4 bg-gray-50">
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          {(totals.upsell.candidates || totals.upsell.offered || totals.upsell.sold) > 0 && (
                            <div className="bg-white p-4 rounded-lg border border-gray-200">
                              <div className="flex items-center space-x-2 mb-3">
                                <IconTrendingUp className="h-4 w-4 text-green-600" />
                                <h4 className="font-semibold text-gray-900">Upselling</h4>
                              </div>
                              <div className="grid grid-cols-3 gap-2 text-sm">
                                <div className="text-center"><div className="font-semibold text-blue-600">{totals.upsell.candidates || 0}</div><div className="text-xs text-gray-500">Opportunities</div></div>
                                <div className="text-center"><div className="font-semibold text-orange-600">{totals.upsell.offered}</div><div className="text-xs text-gray-500">Offered</div></div>
                                <div className="text-center"><div className="font-semibold text-green-600">{totals.upsell.sold}</div><div className="text-xs text-gray-500">Conversions</div></div>
                              </div>
                            </div>
                          )}
                          {(totals.upsize.candidates || totals.upsize.offered || totals.upsize.sold) > 0 && (
                            <div className="bg-white p-4 rounded-lg border border-gray-200">
                              <div className="flex items-center space-x-2 mb-3">
                                <IconTarget className="h-4 w-4 text-blue-600" />
                                <h4 className="font-semibold text-gray-900">Upsizing</h4>
                              </div>
                              <div className="grid grid-cols-3 gap-2 text-sm">
                                <div className="text-center"><div className="font-semibold text-blue-600">{totals.upsize.candidates || 0}</div><div className="text-xs text-gray-500">Opportunities</div></div>
                                <div className="text-center"><div className="font-semibold text-orange-600">{totals.upsize.offered}</div><div className="text-xs text-gray-500">Offered</div></div>
                                <div className="text-center"><div className="font-semibold text-green-600">{totals.upsize.sold}</div><div className="text-xs text-gray-500">Conversions</div></div>
                              </div>
                            </div>
                          )}
                          {(totals.addon.candidates || totals.addon.offered || totals.addon.sold) > 0 && (
                            <div className="bg-white p-4 rounded-lg border border-gray-200">
                              <div className="flex items-center space-x-2 mb-3">
                                <IconShoppingCart className="h-4 w-4 text-purple-600" />
                                <h4 className="font-semibold text-gray-900">Add-ons</h4>
                              </div>
                              <div className="grid grid-cols-3 gap-2 text-sm">
                                <div className="text-center"><div className="font-semibold text-blue-600">{totals.addon.candidates || 0}</div><div className="text-xs text-gray-500">Opportunities</div></div>
                                <div className="text-center"><div className="font-semibold text-orange-600">{totals.addon.offered}</div><div className="text-xs text-gray-500">Offered</div></div>
                                <div className="text-center"><div className="font-semibold text-green-600">{totals.addon.sold}</div><div className="text-xs text-gray-500">Conversions</div></div>
                              </div>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
      {/* Pagination controls */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
        <div className="text-sm text-gray-600">Page {currentPage} of {totalPages}</div>
        <div className="space-x-2">
          <button
            className="px-3 py-1 text-sm rounded border border-gray-300 disabled:opacity-50"
            disabled={currentPage === 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            Previous
          </button>
          <button
            className="px-3 py-1 text-sm rounded border border-gray-300 disabled:opacity-50"
            disabled={currentPage === totalPages}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
};

// Reusable Analytics Report Component
const AnalyticsReportContent = ({ 
  data, 
  title, 
  subtitle 
}: { 
  data: RunAnalytics | WorkerAnalytics, 
  title: string, 
  subtitle?: string 
}) => {
  return (
        <div className="space-y-8">
          {/* Key Metrics Section */}
          <section>
            <div className="mb-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">{title}</h2>
          {subtitle && <p className="text-gray-600">{subtitle}</p>}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MetricCard
                title="Total Transactions"
                value={data.complete_transactions}
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
                value={`${((data.total_successes / Math.max(data.total_offers, 1)) * 100).toFixed(1)}%`}
                subtitle={`${data.total_successes} of ${data.total_offers} offers converted`}
                icon={IconTarget}
                color="primary"
              />
              <MetricCard
                title="Total Offers"
                value={data.total_offers}
                subtitle="Offers made"
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
                        data.upsell_offers > 0 && ((data.upsell_successes / data.upsell_offers) * 100) >= 50
                          ? 'bg-green-100 text-green-800 hover:bg-green-200'
                          : 'bg-red-100 text-red-800 hover:bg-red-200'
                      }`}>
                        {data.upsell_offers > 0 
                          ? `${((data.upsell_successes / data.upsell_offers) * 100).toFixed(1)}%`
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
                        data.upsize_offers > 0 && ((data.upsize_successes / data.upsize_offers) * 100) >= 50
                          ? 'bg-green-100 text-green-800 hover:bg-green-200'
                          : 'bg-red-100 text-red-800 hover:bg-red-200'
                      }`}>
                        {data.upsize_offers > 0 
                          ? `${((data.upsize_successes / data.upsize_offers) * 100).toFixed(1)}%`
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
                        data.addon_offers > 0 && ((data.addon_successes / data.addon_offers) * 100) >= 50
                          ? 'bg-green-100 text-green-800 hover:bg-green-200'
                          : 'bg-red-100 text-red-800 hover:bg-red-200'
                      }`}>
                        {data.addon_offers > 0 
                          ? `${((data.addon_successes / data.addon_offers) * 100).toFixed(1)}%`
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

      {/* Items Suggestively Sold Section */}
      {data.detailed_analytics && (() => {
        // Parse the detailed analytics JSON
        let detailedAnalytics: DetailedAnalytics = {};
        try {
          detailedAnalytics = JSON.parse(data.detailed_analytics);
        } catch (error) {
          console.error('Error parsing detailed analytics:', error);
          return null;
        }

        // Get items with activity
        const itemsWithActivity = Object.entries(detailedAnalytics).filter(([_, itemData]) => {
          const hasSizeActivity = Object.values(itemData.sizes).some(size =>
            size.upsell_base > 0 || size.upsize_base > 0 || size.addon_base > 0 ||
            size.upsell_offered > 0 || size.upsize_offered > 0 || size.addon_offered > 0
          );
          const hasTransitions = itemData.transitions["1_to_2"] > 0 ||
                               itemData.transitions["1_to_3"] > 0 ||
                               itemData.transitions["2_to_3"] > 0;
          return hasSizeActivity || hasTransitions;
        });

        if (itemsWithActivity.length === 0) {
          return null;
        }

        return (
            <section>
              <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Items Suggestively Sold</h2>
              <p className="text-gray-600">Base items, offers made, and items sold through suggestive selling</p>
              </div>

            <div className="space-y-8">
              {/* Items Suggestively Sold Table */}
              <div>
                <ItemsSuggestivelySoldTable items={itemsWithActivity} />
                      </div>

              {/* Size Transition Analysis */}
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Size Upgrade Transitions</h3>
                <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
                  {itemsWithActivity.map(([itemId, itemData]) => (
                    <SizeTransitionCard
                      key={itemId}
                      itemId={itemId}
                      itemName={itemData.name}
                      transitions={itemData.transitions}
                    />
                  ))}
                                </div>
                              </div>
                            </div>
          </section>
        );
      })()}
                              </div>
  );
};

export default function AnalyticsReportPage() {
  const params = useParams()
  const router = useRouter()
  const runId = params.runId as string
  const [isMainReportExpanded, setIsMainReportExpanded] = useState(true)
  const [expandedWorkers, setExpandedWorkers] = useState<Set<string>>(new Set())

  // Worker ID to name mapping
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

  // Get operator from URL search params
  const [searchParams] = React.useState(() => {
    if (typeof window !== 'undefined') {
      return new URLSearchParams(window.location.search)
    }
    return new URLSearchParams()
  })
  const selectedOperator = searchParams.get('operator')

  const { data: analyticsResponse, isLoading, isError, error } = useGetRunAnalytics(runId, !selectedOperator)
  const { data: workerAnalytics, isLoading: isLoadingWorkers, isError: isErrorWorkers } = useGetWorkerAnalytics(runId, selectedOperator || undefined)
  const { data: aiFeedbackResponse, isLoading: isLoadingAIFeedback } = useRunAIFeedback(runId, { enabled: !selectedOperator })

  const handleViewTransactions = () => {
    router.push(`/reports/${runId}/transactions`)
  }

  const handleGoBack = () => {
    router.back()
  }

  const toggleMainReport = () => {
    setIsMainReportExpanded(!isMainReportExpanded)
  }

  const toggleWorker = (workerId: string) => {
    const newExpanded = new Set(expandedWorkers)
    if (newExpanded.has(workerId)) {
      newExpanded.delete(workerId)
    } else {
      newExpanded.add(workerId)
    }
    setExpandedWorkers(newExpanded)
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

  if (!analyticsResponse?.success || !analyticsResponse?.data) {
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

  const data = analyticsResponse.data

  return (
    <RequireAuth>
      <header className="flex h-16 shrink-0 items-center gap-2 border-b transition-[width,height] ease-linear group-has-data-[collapsible=icon]/sidebar-wrapper:h-16">
        <div className="flex items-center gap-2 px-4">
          <h1 className="text-base font-medium">Analytics Report</h1>
        </div>
      </header>
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
                    <p>October 6th, 2025</p>
                                 </span>
                  <span className="text-gray-400">•</span>
                  <span className="text-lg">DQ Cary</span>
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
          {/* Main Report Section - Collapsible (hidden when viewing specific operator) */}
          {!selectedOperator && (
            <section>
              <div className="mb-6">
                <button
                  onClick={toggleMainReport}
                  className="flex items-center space-x-3 text-left w-full hover:bg-gray-50 p-4 rounded-lg transition-colors"
                >
                  {isMainReportExpanded ? (
                    <IconChevronDown className="h-5 w-5 text-gray-600" />
                  ) : (
                    <IconChevronRight className="h-5 w-5 text-gray-600" />
                  )}
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-1">Overall Run Analytics</h2>
                    <p className="text-gray-600">Complete performance overview for all operators</p>
                      </div>
                </button>
                    </div>
              
              {isMainReportExpanded && (
                <AnalyticsReportContent
                  data={data}
                  title="Overall Performance"
                  subtitle="Combined analytics from all operators"
                />
              )}
            </section>
          )}

          {/* AI Feedback Section - Only show when viewing overall report */}
          {!selectedOperator && (
            <section>
              <RunAIFeedbackDisplay
                feedback={aiFeedbackResponse?.data?.feedback}
                runId={runId}
                runDate={data.run_date}
                isLoading={isLoadingAIFeedback}
              />
            </section>
          )}

          {/* Worker Analytics Section */}
          {workerAnalytics?.success && workerAnalytics.data.length > 0 && (
            <section>
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-gray-900 mb-2">
                  {selectedOperator ? `Operator Report: ${workerNameMap[selectedOperator] || selectedOperator}` : "Individual Operator Reports"}
                </h2>
                <p className="text-gray-600">
                  {selectedOperator ? "Performance breakdown for the selected operator" : "Performance breakdown by individual operators"}
                </p>
              </div>
              
              <div className="space-y-6">
                {workerAnalytics.data
                  .filter(workerData => (!selectedOperator || workerData.worker_id === selectedOperator) && workerData.total_transactions > 0)
                  .sort((a, b) => b.total_transactions - a.total_transactions)
                  .map((workerData) => {
                    const isExpanded = selectedOperator ? true : expandedWorkers.has(workerData.worker_id);
                    
                    return (
                      <Card key={workerData.worker_id} className="bg-white border border-gray-200 shadow-sm">
                        {!selectedOperator && (
                          <CardHeader>
                            <button
                              onClick={() => toggleWorker(workerData.worker_id)}
                              className="flex items-center justify-between w-full text-left hover:bg-gray-50 p-2 rounded-lg transition-colors"
                            >
                      <div className="flex items-center space-x-3">
                                {isExpanded ? (
                                  <IconChevronDown className="h-5 w-5 text-gray-600" />
                                ) : (
                                  <IconChevronRight className="h-5 w-5 text-gray-600" />
                                )}
                      <div className="flex items-center space-x-3">
                                  <div className="p-2 bg-blue-100 rounded-lg">
                                    <IconUsers className="h-5 w-5 text-blue-600" />
                        </div>
                                  <div>
                                    <h3 className="text-lg font-semibold text-gray-900">
                                      Operator: {workerNameMap[workerData.worker_id] || workerData.worker_id}
                                    </h3>
                                    <p className="text-sm text-gray-600">
                                      {workerData.total_transactions} transactions • {workerData.total_offers} offers • {workerData.total_successes} successes
                                    </p>
                      </div>
                                  </div>
                                </div>
                              <div className="text-right">
                                <div className="text-lg font-bold text-gray-900">
                                  {((workerData.total_successes / Math.max(workerData.total_offers, 1)) * 100).toFixed(1)}%
                                  </div>
                                <div className="text-sm text-gray-600">Success Rate</div>
                                  </div>
                            </button>
                          </CardHeader>
                        )}
                        
                        {selectedOperator && (
                          <CardHeader>
                      <div className="flex items-center space-x-3">
                        <div className="p-2 bg-blue-100 rounded-lg">
                                <IconUsers className="h-5 w-5 text-blue-600" />
                        </div>
                              <div>
                                <h3 className="text-lg font-semibold text-gray-900">
                                  Operator: {workerNameMap[workerData.worker_id] || workerData.worker_id}
                                </h3>
                                <p className="text-sm text-gray-600">
                                  {workerData.total_transactions} transactions • {workerData.total_offers} offers • {workerData.total_successes} successes
                                </p>
                      </div>
                                  </div>
                            <div className="text-right">
                              <div className="text-lg font-bold text-gray-900">
                                {((workerData.total_successes / Math.max(workerData.total_offers, 1)) * 100).toFixed(1)}%
                                </div>
                              <div className="text-sm text-gray-600">Success Rate</div>
                                  </div>
                          </CardHeader>
                        )}
                        
                        {isExpanded && (
                          <CardContent className={selectedOperator ? "pt-0" : "pt-0"}>
                            <AnalyticsReportContent
                              data={workerData}
                              title={`Operator Performance: ${workerNameMap[workerData.worker_id] || workerData.worker_id}`}
                              subtitle="Individual operator analytics and performance metrics"
                            />
                    </CardContent>
                        )}
                  </Card>
                    );
                  })}
              </div>
            </section>
          )}

          {/* Loading state for worker analytics */}
          {isLoadingWorkers && (
            <section>
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <IconLoader className="h-8 w-8 animate-spin mx-auto mb-4" />
                  <h3 className="text-lg font-semibold">Loading Operator Reports...</h3>
                  <p className="text-muted-foreground">Fetching individual operator analytics</p>
                        </div>
                      </div>
            </section>
          )}

          {/* Error state for worker analytics */}
          {isErrorWorkers && (
            <section>
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <IconAlertCircle className="h-8 w-8 text-yellow-600 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-yellow-600">No Operator Data Available</h3>
                  <p className="text-muted-foreground">Individual operator reports are not available for this run</p>
                </div>
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
    </RequireAuth>
  )
}
