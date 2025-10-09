import { IconTrendingDown, IconTrendingUp } from "@tabler/icons-react"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

interface DashboardMetrics {
  operator_revenue: number
  offer_rate: number
  conversion_rate: number
  items_converted: number
}

interface DashboardTrends {
  operator_revenue_change: number
  offer_rate_change: number
  conversion_rate_change: number
  items_converted_change: number
}

interface SectionCardsProps {
  metrics: DashboardMetrics
  trends?: DashboardTrends
  isLoading?: boolean
}

export function SectionCards({ metrics, trends, isLoading = false }: SectionCardsProps) {
  if (isLoading) {
    return (
      <div className="flex gap-4 px-4 lg:px-6 w-full">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="flex-1 basis-0 animate-pulse">
            <CardHeader>
              <div className="h-4 bg-muted rounded w-24 mb-2"></div>
              <div className="h-8 bg-muted rounded w-32"></div>
            </CardHeader>
          </Card>
        ))}
      </div>
    )
  }

  const formatCurrency = (value: number) => {
    return value.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    })
  }

  const formatPercent = (value: number) => {
    return value.toFixed(1)
  }

  const formatNumber = (value: number) => {
    return value.toLocaleString()
  }

  const getTrendBadge = (change?: number) => {
    if (change === undefined) return null

    const isPositive = change >= 0
    const TrendIcon = isPositive ? IconTrendingUp : IconTrendingDown

    return (
      <Badge variant="outline" className={isPositive ? "text-green-600" : "text-red-600"}>
        <TrendIcon className="size-3" />
        {isPositive ? '+' : ''}{formatPercent(change)}%
      </Badge>
    )
  }

  return (
    <div className="*:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card dark:*:data-[slot=card]:bg-card flex gap-4 px-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:shadow-xs lg:px-6 w-full">
      {/* Operator Revenue */}
      <Card className="@container/card flex-1 basis-0">
        <CardHeader>
          <CardDescription>Operator Revenue</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            ${formatCurrency(metrics.operator_revenue)}
          </CardTitle>
          <div>
            {getTrendBadge(trends?.operator_revenue_change)}
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Extra revenue from upsells
          </div>
          <div className="text-muted-foreground">
            Upsell, upsize & add-ons combined
          </div>
        </CardFooter>
      </Card>

      {/* Offer Rate */}
      <Card className="@container/card flex-1 basis-0">
        <CardHeader>
          <CardDescription>Offer Rate</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {formatPercent(metrics.offer_rate)}%
          </CardTitle>
          <div>
            {getTrendBadge(trends?.offer_rate_change)}
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Staff making offers consistently
          </div>
          <div className="text-muted-foreground">
            Offers made ÷ total opportunities
          </div>
        </CardFooter>
      </Card>

      {/* Conversion Rate */}
      <Card className="@container/card flex-1 basis-0">
        <CardHeader>
          <CardDescription>Conversion Rate</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {formatPercent(metrics.conversion_rate)}%
          </CardTitle>
          <div>
            {getTrendBadge(trends?.conversion_rate_change)}
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Strong customer acceptance
          </div>
          <div className="text-muted-foreground">
            Successful offers ÷ offers made
          </div>
        </CardFooter>
      </Card>

      {/* Items Converted */}
      <Card className="@container/card flex-1 basis-0">
        <CardHeader>
          <CardDescription>Items Converted</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {formatNumber(metrics.items_converted)}
          </CardTitle>
          <div>
            {getTrendBadge(trends?.items_converted_change)}
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Strong upselling performance
          </div>
          <div className="text-muted-foreground">
            Total count of upgraded items
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
