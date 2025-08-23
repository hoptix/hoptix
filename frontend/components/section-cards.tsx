import { IconTrendingDown, IconTrendingUp } from "@tabler/icons-react"

import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

type DataItem = {
  id: number
  date: string
  runId: string
  operatorName: string
  restaurantName: string
  restaurantLocation: string
  totalChances: number
  totalOffers: number
  successfulOffers: number
  offerRate: number
  conversionRate: number
  totalSuccessfulItems: number
}

export function SectionCards({ data }: { data: DataItem[] }) {
  // Calculate aggregated metrics from filtered data
  const totalChances = data.reduce((sum, item) => sum + item.totalChances, 0)
  const totalOffers = data.reduce((sum, item) => sum + item.totalOffers, 0)
  const totalSuccessfulOffers = data.reduce((sum, item) => sum + item.successfulOffers, 0)
  const totalSuccessfulItems = data.reduce((sum, item) => sum + item.totalSuccessfulItems, 0)
  
  const averageOfferRate = totalChances > 0 ? (totalOffers / totalChances) * 100 : 0
  const averageConversionRate = totalOffers > 0 ? (totalSuccessfulOffers / totalOffers) * 100 : 0
  const estimatedRevenue = totalSuccessfulItems * 1.50 // Assuming $1.50 per successful upsell
  
  // Mock trend data (in real app, you'd compare with previous period)
  const trends = {
    revenue: 12.5,
    offerRate: 5.2, 
    conversionRate: 8.3,
    items: 15.2
  }
  return (
    <div className="*:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card dark:*:data-[slot=card]:bg-card grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Operator Revenue</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            ${estimatedRevenue.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </CardTitle>
          <div>
            <Badge variant="outline">
              <IconTrendingUp />
              +{trends.revenue}%
            </Badge>
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Extra revenue from upsells <IconTrendingUp className="size-4" />
          </div>
          <div className="text-muted-foreground">
            Upsell, upsize & add-ons combined
          </div>
        </CardFooter>
      </Card>
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Offer Rate</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {averageOfferRate.toFixed(1)}%
          </CardTitle>
          <div>
            <Badge variant="outline">
              <IconTrendingUp />
              +{trends.offerRate}%
            </Badge>
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Staff making offers consistently <IconTrendingUp className="size-4" />
          </div>
          <div className="text-muted-foreground">
            Offers made ÷ total opportunities
          </div>
        </CardFooter>
      </Card>
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Conversion Rate</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {averageConversionRate.toFixed(1)}%
          </CardTitle>
          <div>
            <Badge variant="outline">
              <IconTrendingUp />
              +{trends.conversionRate}%
            </Badge>
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Strong customer acceptance <IconTrendingUp className="size-4" />
          </div>
          <div className="text-muted-foreground">Successful offers ÷ offers made</div>
        </CardFooter>
      </Card>
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Items Converted</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {totalSuccessfulItems.toLocaleString()}
          </CardTitle>
          <div>
            <Badge variant="outline">
              <IconTrendingUp />
              +{trends.items}%
            </Badge>
          </div>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Strong upselling performance <IconTrendingUp className="size-4" />
          </div>
          <div className="text-muted-foreground">Total count of upgraded items</div>
        </CardFooter>
      </Card>
    </div>
  )
}
