"use client"

import { IconStar, IconTrophy, IconTrendingUp, IconInfoCircle, IconDownload } from "@tabler/icons-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { convertToCSV, downloadCSV, formatDateForCSV, type CSVColumn } from "@/lib/csv-export"

// ============================================================================
// TypeScript Interfaces
// ============================================================================

interface Transaction {
  transaction_id: string
  employee_name: string
  employee_legal_name?: string
  worker_id: string
  transcript: string
  feedback: string

  // Weekly performance metrics
  weekly_upsell_success: number
  weekly_upsell_offers: number
  weekly_upsize_success: number
  weekly_upsize_offers: number
  weekly_addon_success: number
  weekly_addon_offers: number

  // Single transaction metrics
  num_upsell_opportunities: number
  num_upsell_offers: number
  num_upsell_success: number
  num_upsize_opportunities: number
  num_upsize_offers: number
  num_upsize_success: number
  num_addon_opportunities: number
  num_addon_offers: number
  num_addon_success: number

  // Transaction metadata
  begin_time: string
  end_time: string
  items_initial: string
  items_after: string
  num_items_initial: number
  num_items_after: number
  complete_order: number
  score: string
}

interface TopTransactionsHighlightProps {
  locationId: string
  date?: string
  className?: string
}

interface TransactionCardProps {
  transaction: Transaction
  rank: number
}

interface PerformanceMetric {
  label: string
  successes: number
  offers: number
  rate: number
  color: string
}

// ============================================================================
// Hardcoded Data
// ============================================================================

const hardcodedTransactions: Transaction[] = [
  {
    transaction_id: "0005d890-9885-48b6-b275-1e6597f67f38",
    transcript: "Operator: Thank you for stopping. What can I get for you today?\nCustomer: Hey, can I get two four-piece chicken strip baskets, one with ranch and one with honey mustard?\nOperator: Two four-pieces, one with ranch, one with honey mustard?\nCustomer: Yep.\nOperator: What's the drinks for those?\nCustomer: Do y'all have unsweet tea?\nOperator: Yes, ma'am.\nCustomer: Okay, one unsweet tea and one with Sprite.\nOperator: One with unsweet tea, one with Sprite?\nCustomer: Yep. Oh, can we just make both Sprite?\nOperator: Okay.\nCustomer: Yep. And that will do us.\nOperator: All right, that will do us. Appreciate it, ma'am. You're going to be looking at a total of $22.93. Would you like to round up $0.07 for a note in the packet?\nCustomer: Sure.\nOperator: Thank you very much. That's going to be $23 even. Have a great day.\nCustomer: Thank you.\nOperator: Thanks.",
    items_initial: "[\"52_0\",\"52_0\"]",
    num_items_initial: 4,
    items_after: "[\"52_0\",\"52_0\",\"5_1\",\"5_1\"]",
    num_items_after: 6,
    num_upsell_opportunities: 4,
    num_upsell_offers: 2,
    num_upsell_success: 2,
    num_upsize_opportunities: 4,
    num_upsize_offers: 0,
    num_upsize_success: 0,
    num_addon_opportunities: 0,
    num_addon_offers: 0,
    num_addon_success: 0,
    weekly_upsell_success: 47,
    weekly_upsize_success: 23,
    weekly_addon_success: 12,
    weekly_upsell_offers: 80,
    weekly_upsize_offers: 60,
    weekly_addon_offers: 40,
    feedback: "Operator correctly converted both drink upsell opportunities, but did so by assuming the customer wanted drinks rather than explicitly offering them, which diverges from best-practice phrasing. No attempt was made to upsell extra sauces or to upsize the regular fries and small drinks, resulting in four missed upsizing chances. Future calls should include a clear drink add-on question, followed by an offer to make drinks and fries large, and a suggestion of an additional dipping sauce.",
    complete_order: 1,
    score: "0.25",
    worker_id: "80b84d5e-59e2-4e3d-af7e-78f2544cbb23",
    begin_time: "2025-08-31 20:00:51+00",
    end_time: "2025-08-31 20:01:41+00",
    employee_name: "Jamarie Moore",
    employee_legal_name: "Jamarie Moore"
  },
  {
    transaction_id: "003a05bb-c707-4631-a1db-6780d6d44d7c",
    transcript: "Operator: Hi there, no thank you though.\nCustomer: Okay, thank you. I'm ready when you are.\nOperator: Okay, go ahead and order.\nCustomer: Okay, could I just get one thing of pretzel sticks?\nOperator: Okay, my pretzel sticks are $3.89 or you know, do they qualify on my two for five or you can get a sundae with that or a large soft drink or two pretzel sticks two for five.\nCustomer: Oh perfect, yeah, could I also get a chili dog?\nOperator: Okay, so you want to do a chili dog and a pretzel stick?\nCustomer: Uh-huh.\nOperator: Do you want to do another two for five?\nCustomer: Uh, no, actually the other thing I wanted to get was the caramel brownie confection.\nOperator: Oh yeah, these caramel brownie confections, that's good. Do you want to put a little extra heat in there? It makes it really good.\nCustomer: Oh, I would love that. Thank you so much.\nOperator: Hold on a second here. Okay. Anything else for you? Ice cream cone or?\nCustomer: Nope, I think that's about as much as I can take. Thank you so much.\nOperator: Okay, no problem. $13.39 at the window. Thank you.\nCustomer: Thank you.",
    items_initial: "[\"63_0\",\"80_0\"]",
    num_items_initial: 2,
    items_after: "[\"1029_0\",\"80_0\"]",
    num_items_after: 3,
    num_upsell_opportunities: 1,
    num_upsell_offers: 1,
    num_upsell_success: 1,
    num_upsize_opportunities: 0,
    num_upsize_offers: 0,
    num_upsize_success: 0,
    num_addon_opportunities: 1,
    num_addon_offers: 0,
    num_addon_success: 0,
    weekly_upsell_success: 38,
    weekly_upsize_success: 19,
    weekly_addon_success: 8,
    weekly_upsell_offers: 70,
    weekly_upsize_offers: 45,
    weekly_addon_offers: 20,
    feedback: "Operator correctly leveraged the 2 for $5 promotion, made a clear VO-01 upsell offer, and secured an additional chili dog, demonstrating strong upsell execution. No valid upsizing chances were present, and none were missed. One missed opportunity was not offering chargeable toppings for the Cupfection. Continue to suggest dessert add-ons such as extra caramel or whipped cream to maximize ticket averages.",
    complete_order: 1,
    score: "1.0",
    worker_id: "80b84d5e-59e2-4e3d-af7e-78f2544cbb23",
    begin_time: "2025-08-31 19:30:15+00",
    end_time: "2025-08-31 19:31:45+00",
    employee_name: "Maliaka",
    employee_legal_name: "Maliaka"
  },
  {
    transaction_id: "004b700b-f5fb-4cea-b880-530c099ee8d1",
    transcript: "Operator: How can I help you?\nCustomer: Two small cones, one chocolate, one vanilla.\nOperator: Anything else with that?\nCustomer: That's it.\nOperator: That'll be $5.39. Is it to round up for the non-profit charity?\nCustomer: Okay, I'll pull up.",
    items_initial: "[\"7_1\", \"7_1\"]",
    num_items_initial: 2,
    items_after: "[\"7_1\", \"7_1\"]",
    num_items_after: 2,
    num_upsell_opportunities: 0,
    num_upsell_offers: 0,
    num_upsell_success: 0,
    num_upsize_opportunities: 0,
    num_upsize_offers: 0,
    num_upsize_success: 0,
    num_addon_opportunities: 2,
    num_addon_offers: 0,
    num_addon_success: 0,
    weekly_upsell_success: 12,
    weekly_upsize_success: 5,
    weekly_addon_success: 3,
    weekly_upsell_offers: 25,
    weekly_upsize_offers: 15,
    weekly_addon_offers: 10,
    feedback: "The operator correctly entered two small cones and closed the order but made no suggestive-selling attempts. Each cone allowed an add-on of sprinkles, yet no topping offer was presented. Although size was specified, the operator could still phrase a compliant large-size confirmation. To improve performance, explicitly offer sprinkles and use proper upsizing language when appropriate while maintaining the charity ask at the end.",
    complete_order: 1,
    score: "0.0",
    worker_id: "80b84d5e-59e2-4e3d-af7e-78f2544cbb23",
    begin_time: "2025-08-31 18:45:30+00",
    end_time: "2025-08-31 18:46:15+00",
    employee_name: "Latasha Williams",
    employee_legal_name: "Latasha Williams"
  },
  {
    transaction_id: "005c8f12-4d21-4f11-9c3e-7d89e4567891",
    transcript: "Operator: Welcome to Dairy Queen! How are you doing today?\nCustomer: Good, thanks! Can I get a large Blizzard?\nOperator: Absolutely! What flavor would you like?\nCustomer: Oreo, please.\nOperator: Great choice! Would you like to add a second Blizzard for half price today?\nCustomer: No, just the one.\nOperator: No problem! That'll be $6.89 at the window.",
    items_initial: "[\"16_3\"]",
    num_items_initial: 1,
    items_after: "[\"16_3\"]",
    num_items_after: 1,
    num_upsell_opportunities: 1,
    num_upsell_offers: 1,
    num_upsell_success: 0,
    num_upsize_opportunities: 0,
    num_upsize_offers: 0,
    num_upsize_success: 0,
    num_addon_opportunities: 1,
    num_addon_offers: 0,
    num_addon_success: 0,
    weekly_upsell_success: 32,
    weekly_upsize_success: 18,
    weekly_addon_success: 14,
    weekly_upsell_offers: 65,
    weekly_upsize_offers: 50,
    weekly_addon_offers: 35,
    feedback: "Operator provided excellent customer service with a friendly greeting and made an upsell attempt with the half-price Blizzard offer. However, missed an opportunity to suggest toppings or mix-ins for the Blizzard. Continue with the positive energy and consider offering customization options to increase add-on success.",
    complete_order: 1,
    score: "0.85",
    worker_id: "91c95e6f-6a13-5f4e-bg8f-89g3655dcc34",
    begin_time: "2025-08-31 17:15:22+00",
    end_time: "2025-08-31 17:16:05+00",
    employee_name: "Marcus Johnson",
    employee_legal_name: "Marcus Johnson"
  },
  {
    transaction_id: "006d9f23-5e32-5g22-ad4f-8e90f5678902",
    transcript: "Operator: Hi, what can I get started for you?\nCustomer: I'll have a cheeseburger meal.\nOperator: Would you like to make that a large meal?\nCustomer: Sure.\nOperator: And what drink would you like?\nCustomer: Coke, please.\nOperator: Perfect! Anything else today?\nCustomer: That's all.\nOperator: Great! Your total is $9.45.",
    items_initial: "[\"1001_2\"]",
    num_items_initial: 3,
    items_after: "[\"1001_3\"]",
    num_items_after: 3,
    num_upsell_opportunities: 0,
    num_upsell_offers: 0,
    num_upsell_success: 0,
    num_upsize_opportunities: 1,
    num_upsize_offers: 1,
    num_upsize_success: 1,
    num_addon_opportunities: 0,
    num_addon_offers: 0,
    num_addon_success: 0,
    weekly_upsell_success: 28,
    weekly_upsize_success: 35,
    weekly_addon_success: 6,
    weekly_upsell_offers: 55,
    weekly_upsize_offers: 70,
    weekly_addon_offers: 18,
    feedback: "Excellent upsizing execution! Operator successfully converted the upsize opportunity with clear, confident language. No missed opportunities in this transaction. Keep up the great work with proactive sizing suggestions.",
    complete_order: 1,
    score: "0.95",
    worker_id: "a2d06f70-7b24-6g5f-ch9g-90h4766edd45",
    begin_time: "2025-08-31 16:30:18+00",
    end_time: "2025-08-31 16:31:02+00",
    employee_name: "Sarah Chen",
    employee_legal_name: "Sarah Chen"
  },
  {
    transaction_id: "007e0g34-6f43-6h33-be5g-9f01g6789013",
    transcript: "Operator: Welcome! What would you like today?\nCustomer: Just a small fry.\nOperator: Okay, one small fry. That's $2.19.\nCustomer: Thanks.\nOperator: See you at the window.",
    items_initial: "[\"25_1\"]",
    num_items_initial: 1,
    items_after: "[\"25_1\"]",
    num_items_after: 1,
    num_upsell_opportunities: 2,
    num_upsell_offers: 0,
    num_upsell_success: 0,
    num_upsize_opportunities: 1,
    num_upsize_offers: 0,
    num_upsize_success: 0,
    num_addon_opportunities: 1,
    num_addon_offers: 0,
    num_addon_success: 0,
    weekly_upsell_success: 8,
    weekly_upsize_success: 4,
    weekly_addon_success: 2,
    weekly_upsell_offers: 30,
    weekly_upsize_offers: 25,
    weekly_addon_offers: 12,
    feedback: "Missed multiple opportunities for suggestive selling. Should have offered to upsize the fries, suggested a drink or burger to complete a meal, and mentioned sauce options. This was a short transaction with potential for significant ticket growth through proper upselling techniques.",
    complete_order: 1,
    score: "0.15",
    worker_id: "b3e17g81-8c35-7i6g-di0h-a1i5877fee56",
    begin_time: "2025-08-31 15:45:40+00",
    end_time: "2025-08-31 15:46:08+00",
    employee_name: "Tyler Brooks",
    employee_legal_name: "Tyler Brooks"
  },
  {
    transaction_id: "008f1h45-7g54-7j44-cf6h-0g12h7890124",
    transcript: "Operator: Hi there! Thanks for choosing Dairy Queen. What can I get for you?\nCustomer: I want a medium Blizzard.\nOperator: Awesome! What flavor?\nCustomer: Reese's.\nOperator: Great! Would you like to make that a large for just 50 cents more?\nCustomer: Yeah, why not!\nOperator: Perfect! And can I add some extra Reese's pieces on top for you?\nCustomer: Sure!\nOperator: Excellent choice! Anything else?\nCustomer: No, that's it.\nOperator: Your total is $7.89. Thank you!",
    items_initial: "[\"16_2\"]",
    num_items_initial: 1,
    items_after: "[\"16_3\", \"9017_0\"]",
    num_items_after: 2,
    num_upsell_opportunities: 0,
    num_upsell_offers: 0,
    num_upsell_success: 0,
    num_upsize_opportunities: 1,
    num_upsize_offers: 1,
    num_upsize_success: 1,
    num_addon_opportunities: 1,
    num_addon_offers: 1,
    num_addon_success: 1,
    weekly_upsell_success: 42,
    weekly_upsize_success: 38,
    weekly_addon_success: 22,
    weekly_upsell_offers: 68,
    weekly_upsize_offers: 58,
    weekly_addon_offers: 42,
    feedback: "Outstanding performance! Operator successfully executed both upsize and add-on opportunities with enthusiastic, value-focused language. The mention of 'just 50 cents more' effectively justified the upsize. Excellent example of maximizing transaction value through confident suggestive selling.",
    complete_order: 1,
    score: "1.0",
    worker_id: "c4f28h92-9d46-8k7h-ej1i-b2j6988gff67",
    begin_time: "2025-08-31 14:20:15+00",
    end_time: "2025-08-31 14:21:10+00",
    employee_name: "Jessica Martinez",
    employee_legal_name: "Jessica Martinez"
  },
  {
    transaction_id: "009g2i56-8h65-8l55-dg7i-1h23i8901235",
    transcript: "Operator: Welcome to DQ. What can I get you?\nCustomer: Two kids meals please.\nOperator: Sure thing. What would the kids like in their meals?\nCustomer: Both chicken strips.\nOperator: Drinks?\nCustomer: Two apple juices.\nOperator: Got it. That'll be $8.98.",
    items_initial: "[\"1015_0\", \"1015_0\"]",
    num_items_initial: 6,
    items_after: "[\"1015_0\", \"1015_0\"]",
    num_items_after: 6,
    num_upsell_opportunities: 1,
    num_upsell_offers: 0,
    num_upsell_success: 0,
    num_upsize_opportunities: 0,
    num_upsize_offers: 0,
    num_upsize_success: 0,
    num_addon_opportunities: 2,
    num_addon_offers: 0,
    num_addon_success: 0,
    weekly_upsell_success: 18,
    weekly_upsize_success: 12,
    weekly_addon_success: 9,
    weekly_upsell_offers: 48,
    weekly_upsize_offers: 38,
    weekly_addon_offers: 28,
    feedback: "Transaction was processed correctly but lacked suggestive selling. Could have offered dipping sauces for the chicken strips or suggested an adult meal for the parent. Even with kids meals, there are opportunities to increase ticket value through thoughtful recommendations.",
    complete_order: 1,
    score: "0.45",
    worker_id: "d5g39i03-a1e57-9m8i-fk2j-c3k7099hgg78",
    begin_time: "2025-08-31 13:10:25+00",
    end_time: "2025-08-31 13:11:15+00",
    employee_name: "David Kim",
    employee_legal_name: "David Kim"
  }
]

// ============================================================================
// Utility Functions
// ============================================================================

const calculateRate = (success: number, offers: number): number => {
  if (offers === 0) return 0
  return Math.round((success / offers) * 100)
}

const getRankBadgeColor = (rank: number): string => {
  switch (rank) {
    case 1: return "bg-gradient-to-r from-yellow-100 to-yellow-200 text-yellow-800 border-yellow-300"
    case 2: return "bg-gradient-to-r from-gray-100 to-gray-200 text-gray-800 border-gray-300"
    case 3: return "bg-gradient-to-r from-orange-100 to-orange-200 text-orange-800 border-orange-300"
    default: return "bg-gradient-to-r from-blue-100 to-blue-200 text-blue-800 border-blue-300"
  }
}

const getRankIcon = (rank: number): JSX.Element => {
  switch (rank) {
    case 1: return <IconTrophy className="h-4 w-4 text-yellow-600" />
    case 2:
    case 3: return <IconStar className="h-4 w-4" />
    default: return <IconTrendingUp className="h-4 w-4" />
  }
}

const calculateWeeklyPerformance = (transaction: Transaction): number => {
  const totalSuccess = transaction.weekly_upsell_success + transaction.weekly_upsize_success + transaction.weekly_addon_success
  const totalOffers = transaction.weekly_upsell_offers + transaction.weekly_upsize_offers + transaction.weekly_addon_offers

  if (totalOffers === 0) return 0
  return Math.round((totalSuccess / totalOffers) * 100)
}

// ============================================================================
// Transaction Card Component
// ============================================================================

const TransactionCard = ({ transaction, rank }: TransactionCardProps) => {
  const weeklyPerformance = calculateWeeklyPerformance(transaction)

  const metrics: PerformanceMetric[] = [
    {
      label: "Upsell",
      successes: transaction.weekly_upsell_success,
      offers: transaction.weekly_upsell_offers,
      rate: calculateRate(transaction.weekly_upsell_success, transaction.weekly_upsell_offers),
      color: "emerald"
    },
    {
      label: "Upsize",
      successes: transaction.weekly_upsize_success,
      offers: transaction.weekly_upsize_offers,
      rate: calculateRate(transaction.weekly_upsize_success, transaction.weekly_upsize_offers),
      color: "blue"
    },
    {
      label: "Add-ons",
      successes: transaction.weekly_addon_success,
      offers: transaction.weekly_addon_offers,
      rate: calculateRate(transaction.weekly_addon_success, transaction.weekly_addon_offers),
      color: "violet"
    }
  ]

  return (
    <div className="group relative flex-shrink-0 w-[320px] snap-start">
      <div className="min-h-[240px] border border-gray-200 rounded-xl p-4 bg-white hover:shadow-xl hover:border-gray-300 transition-all duration-300 flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <Badge className={`${getRankBadgeColor(rank)} font-semibold text-xs px-2 py-1 border`}>
            <div className="flex items-center gap-1.5">
              {getRankIcon(rank)}
              <span>#{rank}</span>
            </div>
          </Badge>
          <h3 className="font-semibold text-sm text-gray-900 truncate ml-2 flex-1" title={transaction.employee_name}>
            {transaction.employee_name}
          </h3>
        </div>

        {/* Weekly Performance Score */}
        <div className="mb-4 text-center">
          <div className="inline-flex items-baseline gap-1">
            <span className="text-4xl font-bold bg-gradient-to-r from-emerald-600 to-teal-600 bg-clip-text text-transparent">
              {weeklyPerformance}
            </span>
            <span className="text-xl font-semibold text-gray-400">%</span>
          </div>
          <p className="text-xs text-gray-500 mt-1">Weekly Success Rate</p>
        </div>

        {/* Performance Metrics */}
        <div className="flex-1 space-y-2">
          {metrics.map((metric) => (
            <div
              key={metric.label}
              className={`flex items-center justify-between px-3 py-1.5 rounded-lg bg-${metric.color}-50 border border-${metric.color}-100`}
            >
              <span className={`text-xs font-medium text-${metric.color}-700`}>{metric.label}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-gray-600" title={`${metric.successes} successes out of ${metric.offers} offers`}>
                  {metric.successes}/{metric.offers}
                </span>
                <span className={`text-xs font-bold text-${metric.color}-700 min-w-[32px] text-right`}>
                  {metric.rate}%
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Action Button */}
        <div className="mt-3 pt-3 border-t border-gray-100">
          <Dialog>
            <DialogTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="w-full h-8 text-xs font-medium hover:bg-gray-100"
              >
                View Details →
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Badge className={`${getRankBadgeColor(rank)} font-semibold border`}>
                    <div className="flex items-center gap-1">
                      {getRankIcon(rank)}
                      <span>#{rank}</span>
                    </div>
                  </Badge>
                  <span>Transaction Details - {transaction.employee_name}</span>
                </DialogTitle>
                <DialogDescription>
                  Complete transaction analysis and performance breakdown
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6">
                {/* Performance Metrics */}
                <div className="grid grid-cols-2 gap-6">
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold">Weekly Performance</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center p-3 bg-emerald-50 rounded-lg border border-emerald-100">
                        <span className="font-medium text-sm">Upsell Success</span>
                        <span className="text-lg font-bold text-emerald-700">
                          {transaction.weekly_upsell_success}/{transaction.weekly_upsell_offers}
                        </span>
                      </div>
                      <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg border border-blue-100">
                        <span className="font-medium text-sm">Upsize Success</span>
                        <span className="text-lg font-bold text-blue-700">
                          {transaction.weekly_upsize_success}/{transaction.weekly_upsize_offers}
                        </span>
                      </div>
                      <div className="flex justify-between items-center p-3 bg-violet-50 rounded-lg border border-violet-100">
                        <span className="font-medium text-sm">Add-ons Success</span>
                        <span className="text-lg font-bold text-violet-700">
                          {transaction.weekly_addon_success}/{transaction.weekly_addon_offers}
                        </span>
                      </div>
                      <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-200">
                        <span className="font-medium text-sm">Overall Success Rate</span>
                        <span className="text-lg font-bold text-gray-900">{weeklyPerformance}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold">This Transaction</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                        <span className="font-medium text-sm">Initial Items</span>
                        <span className="font-bold">{transaction.num_items_initial}</span>
                      </div>
                      <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                        <span className="font-medium text-sm">Final Items</span>
                        <span className="font-bold">{transaction.num_items_after}</span>
                      </div>
                      <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                        <span className="font-medium text-sm">Upsell Opportunities</span>
                        <span className="font-bold">{transaction.num_upsell_opportunities}</span>
                      </div>
                      <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                        <span className="font-medium text-sm">Upsell Success</span>
                        <span className="font-bold text-emerald-600">
                          {transaction.num_upsell_success}/{transaction.num_upsell_offers}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Feedback */}
                {transaction.feedback && (
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold">AI Feedback</h3>
                    <div className="bg-blue-50 border border-blue-100 p-4 rounded-lg">
                      <p className="text-sm leading-relaxed text-gray-700">{transaction.feedback}</p>
                    </div>
                  </div>
                )}

                {/* Transcript */}
                {transaction.transcript && (
                  <div className="space-y-2">
                    <h3 className="text-lg font-semibold">Transcript</h3>
                    <div className="bg-gray-50 border border-gray-200 p-4 rounded-lg max-h-60 overflow-y-auto">
                      <pre className="text-sm whitespace-pre-wrap font-mono text-gray-700">
                        {transaction.transcript}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>
    </div>
  )
}

// ============================================================================
// Main Component
// ============================================================================

export function TopTransactionsHighlight({ locationId, date, className }: TopTransactionsHighlightProps) {
  const transactions = hardcodedTransactions

  const csvColumns: CSVColumn[] = [
    { key: 'transaction_id', label: 'Transaction ID' },
    { key: 'employee_name', label: 'Employee Name' },
    { key: 'begin_time', label: 'Start Time', transform: formatDateForCSV },
    { key: 'end_time', label: 'End Time', transform: formatDateForCSV },
    { key: 'score', label: 'Base Score' },
    { key: 'weekly_upsell_success', label: 'Weekly Upsell Success' },
    { key: 'weekly_upsell_offers', label: 'Weekly Upsell Offers' },
    { key: 'weekly_upsize_success', label: 'Weekly Upsize Success' },
    { key: 'weekly_upsize_offers', label: 'Weekly Upsize Offers' },
    { key: 'weekly_addon_success', label: 'Weekly Addon Success' },
    { key: 'weekly_addon_offers', label: 'Weekly Addon Offers' },
    { key: 'num_upsell_opportunities', label: 'Transaction Upsell Opportunities' },
    { key: 'num_upsell_success', label: 'Transaction Upsell Success' },
    { key: 'feedback', label: 'Feedback' },
  ]

  const exportTopTransactions = () => {
    if (!transactions.length) return

    const csv = convertToCSV(transactions, csvColumns)
    const timestamp = new Date().toISOString().slice(0, 10)
    const filename = `top_transactions_${locationId}_${date || timestamp}.csv`

    downloadCSV(csv, filename)
  }

  if (!locationId) {
    return null
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <IconTrophy className="h-5 w-5 text-yellow-600" />
              <span>Operator Performance This Week</span>
            </CardTitle>
            <CardDescription>Weekly success rates for all operators</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={exportTopTransactions}
              disabled={!transactions.length}
            >
              <IconDownload className="h-4 w-4 mr-2" />
              Export
            </Button>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <button className="p-1 hover:bg-gray-100 rounded">
                    <IconInfoCircle className="h-5 w-5 text-gray-400" />
                  </button>
                </TooltipTrigger>
                <TooltipContent className="max-w-sm">
                  <div className="space-y-2">
                    <div className="font-semibold">Performance Metrics</div>
                    <div className="text-xs space-y-1">
                      <div>• Success Rate = Total Successes / Total Offers</div>
                      <div>• Based on weekly aggregated performance</div>
                      <div>• Includes upsell, upsize, and add-on metrics</div>
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </CardHeader>

      <CardContent className="py-6 overflow-hidden">
        <div className="w-full min-w-0">
          <div className="flex overflow-x-auto overflow-y-visible scroll-smooth snap-x snap-mandatory gap-4 py-1 pb-2">
            {transactions.map((transaction, index) => (
              <TransactionCard
                key={transaction.transaction_id}
                transaction={transaction}
                rank={index + 1}
              />
            ))}
          </div>
        </div>

        {transactions.length > 0 && (
          <div className="mt-6 pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center">
              Showing {transactions.length} operator{transactions.length !== 1 ? 's' : ''} • Scroll horizontally to view all
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
