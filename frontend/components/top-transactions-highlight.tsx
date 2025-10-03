"use client"

import { IconStar, IconTrophy, IconClock, IconUser, IconTrendingUp, IconInfoCircle, IconDownload, IconEye } from "@tabler/icons-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { useGetTopTransactions, type TopTransaction } from "@/hooks/getTopTransactions"
import { convertToCSV, downloadCSV, formatDateForCSV, type CSVColumn } from "@/lib/csv-export"
import { format } from "date-fns"

// Hardcoded transaction data
const hardcodedTransactions = [
  {
    idx: 0,
    transaction_id: "0005d890-9885-48b6-b275-1e6597f67f38",
    transcript: "Operator: Thank you for stopping. What can I get for you today?\nCustomer: Hey, can I get two four-piece chicken strip baskets, one with ranch and one with honey mustard?\nOperator: Two four-pieces, one with ranch, one with honey mustard?\nCustomer: Yep.\nOperator: What's the drinks for those?\nCustomer: Do y'all have unsweet tea?\nOperator: Yes, ma'am.\nCustomer: Okay, one unsweet tea and one with Sprite.\nOperator: One with unsweet tea, one with Sprite?\nCustomer: Yep. Oh, can we just make both Sprite?\nOperator: Okay.\nCustomer: Yep. And that will do us.\nOperator: All right, that will do us. Appreciate it, ma'am. You're going to be looking at a total of $22.93. Would you like to round up $0.07 for a note in the packet?\nCustomer: Sure.\nOperator: Thank you very much. That's going to be $23 even. Have a great day.\nCustomer: Thank you.\nOperator: Thanks.",
    details: "{\"issues\": \"Upselling scenario reference: Scenario VO-02 DrinkCB table row; Upsizing reference: Scenario VO-02 Drink and VO-04 Side; Item IDs referenced from items.json: 52 (4-piece chicken strip basket), 5 (drink), 25 (fries), 9008 (dipping sauce). Difficulties: transcript lacked drink sizes so smallest size was assumed per rules; fries size inferred as regular from basket definition; deciding whether operator's wording counted as a valid upsell required judgement; accounting for potential extra dipping sauce upsell though the customer had already selected one sauce required interpretation.\", \"feedback\": \"Operator correctly converted both drink upsell opportunities, but did so by assuming the customer wanted drinks rather than explicitly offering them, which diverges from best-practice phrasing. No attempt was made to upsell extra sauces or to upsize the regular fries and small drinks, resulting in four missed upsizing chances. Future calls should include a clear drink add-on question, followed by an offer to make drinks and fries large, and a suggestion of an additional dipping sauce.\", \"gpt_price\": 0, \"video_link\": \"\", \"coupon_used\": 0, \"items_after\": \"[\\\"52_0\\\",\\\"52_0\\\",\\\"5_1\\\",\\\"5_1\\\"]\", \"items_upsold\": \"[\\\"5_1\\\",\\\"5_1\\\"]\", \"mobile_order\": 0, \"items_initial\": \"[\\\"52_0\\\",\\\"52_0\\\"]\", \"complete_order\": 1, \"asked_more_time\": 0, \"items_addonable\": 0, \"num_items_after\": 6, \"video_file_path\": \"\", \"items_upsellable\": \"[\\\"5_1\\\",\\\"9008_0\\\",\\\"5_1\\\",\\\"9008_0\\\"]\", \"items_upsizeable\": \"[\\\"5_1\\\",\\\"5_1\\\",\\\"25_2\\\",\\\"25_2\\\"]\", \"num_addon_offers\": 0, \"num_addon_success\": 0, \"num_items_initial\": 4, \"num_upsell_offers\": 2, \"num_upsize_offers\": 0, \"reasoning_summary\": \"\", \"num_largest_offers\": 0, \"num_upsell_success\": 2, \"num_upsize_success\": 0, \"out_of_stock_items\": \"0\", \"items_addon_success\": 0, \"items_addon_creators\": 0, \"items_upsize_success\": 0, \"items_upsize_creators\": 0, \"items_upsold_creators\": [\"52_0\", \"52_0\"], \"items_upsizing_creators\": [\"5_1\", \"5_1\", \"25_2\", \"25_2\"], \"num_addon_opportunities\": 0, \"items_upselling_creators\": [\"52_0\", \"52_0\", \"52_0\", \"52_0\"], \"num_upsell_opportunities\": 4, \"num_upsize_opportunities\": 4, \"items_addon_final_creators\": 0}",
    items_initial: "[\"52_0\",\"52_0\"]",
    num_items_initial: 4,
    items_after: "[\"52_0\",\"52_0\",\"5_1\",\"5_1\"]",
    num_items_after: 6,
    num_upsell_opportunities: 4,
    num_upsell_offers: 2,
    num_upsell_success: 2,
    num_largest_offers: 0,
    num_upsize_opportunities: 4,
    num_upsize_offers: 0,
    num_upsize_success: 0,
    num_addon_opportunities: 0,
    num_addon_offers: 0,
    num_addon_success: 0,
    // Weekly totals for display
    weekly_upsell_success: 47,
    weekly_upsize_success: 23,
    weekly_addon_success: 12,
    weekly_upsell_offers: 80,
    weekly_upsize_offers: 60,
    weekly_addon_offers: 40,
    feedback: "Operator correctly converted both drink upsell opportunities, but did so by assuming the customer wanted drinks rather than explicitly offering them, which diverges from best-practice phrasing. No attempt was made to upsell extra sauces or to upsize the regular fries and small drinks, resulting in four missed upsizing chances. Future calls should include a clear drink add-on question, followed by an offer to make drinks and fries large, and a suggestion of an additional dipping sauce.",
    issues: "Upselling scenario reference: Scenario VO-02 DrinkCB table row; Upsizing reference: Scenario VO-02 Drink and VO-04 Side; Item IDs referenced from items.json: 52 (4-piece chicken strip basket), 5 (drink), 25 (fries), 9008 (dipping sauce). Difficulties: transcript lacked drink sizes so smallest size was assumed per rules; fries size inferred as regular from basket definition; deciding whether operator's wording counted as a valid upsell required judgement; accounting for potential extra dipping sauce upsell though the customer had already selected one sauce required interpretation.",
    complete_order: 1,
    mobile_order: 0,
    coupon_used: 0,
    asked_more_time: 0,
    out_of_stock_items: "0",
    gpt_price: "89.152",
    reasoning_summary: "",
    video_file_path: "",
    video_link: "",
    score: "0.25",
    upsell_offered_items: null,
    upsize_offered_items: null,
    addon_offered_items: null,
    upsell_candidate_items: null,
    upsize_candidate_items: null,
    addon_candidate_items: null,
    upsell_base_items: null,
    upsize_base_items: null,
    addon_base_items: null,
    upsell_success_items: null,
    upsize_success_items: null,
    addon_success_items: null,
    worker_id: "80b84d5e-59e2-4e3d-af7e-78f2544cbb23",
    begin_time: "2025-08-31 20:00:51+00",
    end_time: "2025-08-31 20:01:41+00",
    video_id: "f3c584e2-89b9-41b5-92c4-b8344ac5983f",
    run_id: "9ba8c21f-3991-4aa9-8c56-c6d8374c72d3",
    transaction_kind: "order",
    transaction_meta: "{\"text\": \"Operator: Thank you for stopping. What can I get for you today?\\nCustomer: Hey, can I get two four-piece chicken strip baskets, one with ranch and one with honey mustard?\\nOperator: Two four-pieces, one with ranch, one with honey mustard?\\nCustomer: Yep.\\\\nOperator: What's the drinks for those?\\\\nCustomer: Do y'all have unsweet tea?\\\\nOperator: Yes, ma'am.\\\\nCustomer: Okay, one unsweet tea and one with Sprite.\\\\nOperator: One with unsweet tea, one with Sprite?\\\\nCustomer: Yep. Oh, can we just make both Sprite?\\\\nOperator: Okay.\\\\nCustomer: Yep. And that will do us.\\\\nOperator: All right, that will do us. Appreciate it, ma'am. You're going to be looking at a total of $22.93. Would you like to round up $0.07 for a note in the packet?\\\\nCustomer: Sure.\\\\nOperator: Thank you very much. That's going to be $23 even. Have a great day.\\\\nCustomer: Thank you.\\\\nOperator: Thanks.\\\",\\\"2\\\":\\\"1\\\",\\\"3\\\":\\\"0\\\",\\\"4\\\":\\\"0\\\",\\\"5\\\":\\\"0\\\",\\\"6\\\":\\\"0\\\",\\\"7\\\":\\\"N/A\\\"}\", \"coupon_used\": 0, \"mobile_order\": 0, \"segment_index\": 1, \"complete_order\": 1, \"asked_more_time\": 0, \"video_end_seconds\": 100.0, \"out_of_stock_items\": \"0\", \"video_start_seconds\": 50.0, \"total_segments_in_video\": 3}",
    clip_s3_url: null,
    employee_id: "80b84d5e-59e2-4e3d-af7e-78f2544cbb23",
    employee_name: "Jamarie Moore",
    employee_legal_name: "Jamarie Moore"
  },
  {
    idx: 1,
    transaction_id: "003a05bb-c707-4631-a1db-6780d6d44d7c",
    transcript: "Operator: Hi there, no thank you though.\nCustomer: Okay, thank you. I'm ready when you are.\nOperator: Okay, go ahead and order.\nCustomer: Okay, could I just get one thing of pretzel sticks?\nOperator: Okay, my pretzel sticks are $3.89 or you know, do they qualify on my two for five or you can get a sundae with that or a large soft drink or two pretzel sticks two for five.\nCustomer: Oh perfect, yeah, could I also get a chili dog?\nOperator: Okay, so you want to do a chili dog and a pretzel stick?\nCustomer: Uh-huh.\nOperator: Do you want to do another two for five?\nCustomer: Uh, no, actually the other thing I wanted to get was the caramel brownie confection.\nOperator: Oh yeah, these caramel brownie confections, that's good. Do you want to put a little extra heat in there? It makes it really good.\nCustomer: Oh, I would love that. Thank you so much.\nOperator: Hold on a second here. Okay. Anything else for you? Ice cream cone or?\nCustomer: Nope, I think that's about as much as I can take. Thank you so much.\nOperator: Okay, no problem. $13.39 at the window. Thank you.\nCustomer: Thank you.",
    details: "{\"issues\": \"Upselling reference: Scenario VO-01 (2for5) in Upselling Scenarios table. Item IDs and topping ID verified in Items JSON (Pretzel 63, Chili Dog 65, Cupfection 80, Primary Topping 9017). Meal ID 1029 from Meals JSON. No applicable upsizing scenarios per Upsizing Scenarios table. Ambiguity: 'extra heat' on Cupfection interpreted as non-chargeable preparation note, not a topping upsell.\", \"feedback\": \"Operator correctly leveraged the 2 for $5 promotion, made a clear VO-01 upsell offer, and secured an additional chili dog, demonstrating strong upsell execution. No valid upsizing chances were present, and none were missed. One missed opportunity was not offering chargeable toppings for the Cupfection. Continue to suggest dessert add-ons such as extra caramel or whipped cream to maximize ticket averages.\", \"gpt_price\": 0, \"video_link\": \"\", \"coupon_used\": 0, \"items_after\": \"[\\\"1029_0\\\",\\\"80_0\\\"]\", \"items_upsold\": \"[\\\"65_0\\\"]\", \"mobile_order\": 0, \"items_initial\": \"[\\\"63_0\\\",\\\"80_0\\\"]\", \"complete_order\": 1, \"asked_more_time\": 1, \"items_addonable\": \"[\\\"9017_0\\\"]\", \"num_items_after\": 3, \"video_file_path\": \"\", \"items_upsellable\": \"[\\\"60_1\\\",\\\"63_0\\\",\\\"65_0\\\",\\\"64_0\\\"]\", \"items_upsizeable\": 0, \"num_addon_offers\": 0, \"num_addon_success\": 0, \"num_items_initial\": 2, \"num_upsell_offers\": 1, \"num_upsize_offers\": 0, \"reasoning_summary\": \"\", \"num_largest_offers\": 0, \"num_upsell_success\": 1, \"num_upsize_success\": 0, \"out_of_stock_items\": \"0\", \"items_addon_success\": 0, \"items_addon_creators\": [\"80_0\"], \"items_upsize_success\": 0, \"items_upsize_creators\": 0, \"items_upsold_creators\": [\"63_0\"], \"items_upsizing_creators\": 0, \"num_addon_opportunities\": 1, \"items_upselling_creators\": [\"63_0\"], \"num_upsell_opportunities\": 1, \"num_upsize_opportunities\": 0, \"items_addon_final_creators\": 0}",
    items_initial: "[\"63_0\",\"80_0\"]",
    num_items_initial: 2,
    items_after: "[\"1029_0\",\"80_0\"]",
    num_items_after: 3,
    num_upsell_opportunities: 1,
    num_upsell_offers: 1,
    num_upsell_success: 1,
    num_largest_offers: 0,
    num_upsize_opportunities: 0,
    num_upsize_offers: 0,
    num_upsize_success: 0,
    num_addon_opportunities: 1,
    num_addon_offers: 0,
    num_addon_success: 0,
    // Weekly totals for display
    weekly_upsell_success: 38,
    weekly_upsize_success: 19,
    weekly_addon_success: 8,
    weekly_upsell_offers: 70,
    weekly_upsize_offers: 45,
    weekly_addon_offers: 20,
    feedback: "Operator correctly leveraged the 2 for $5 promotion, made a clear VO-01 upsell offer, and secured an additional chili dog, demonstrating strong upsell execution. No valid upsizing chances were present, and none were missed. One missed opportunity was not offering chargeable toppings for the Cupfection. Continue to suggest dessert add-ons such as extra caramel or whipped cream to maximize ticket averages.",
    complete_order: 1,
    mobile_order: 0,
    coupon_used: 0,
    asked_more_time: 1,
    out_of_stock_items: "0",
    gpt_price: "66.294",
    reasoning_summary: "",
    video_file_path: "",
    video_link: "",
    score: "1.0",
    upsell_offered_items: null,
    upsize_offered_items: null,
    addon_offered_items: null,
    upsell_candidate_items: null,
    upsize_candidate_items: null,
    addon_candidate_items: null,
    upsell_base_items: null,
    upsize_base_items: null,
    addon_base_items: null,
    upsell_success_items: null,
    upsize_success_items: null,
    addon_success_items: null,
    worker_id: "80b84d5e-59e2-4e3d-af7e-78f2544cbb23",
    begin_time: "2025-08-31 19:30:15+00",
    end_time: "2025-08-31 19:31:45+00",
    employee_name: "Maliaka",
    employee_legal_name: "Maliaka"
  },
  {
    idx: 2,
    transaction_id: "004b700b-f5fb-4cea-b880-530c099ee8d1",
    transcript: "Operator: How can I help you?\nCustomer: Two small cones, one chocolate, one vanilla.\nOperator: Anything else with that?\nCustomer: That's it.\nOperator: That'll be $5.39. Is it to round up for the non-profit charity?\nCustomer: Okay, I'll pull up.",
    details: "{\"issues\": \"Item information sourced from items.json: Cone (Item ID 7) indicates add-on sprinkles and upsizing to large; Additional Topping list shows Sprinkles (Item ID 9003). No upselling scenarios matched this order. No conflicting instructions encountered.\", \"feedback\": \"The operator correctly entered two small cones and closed the order but made no suggestive-selling attempts. Each cone allowed an add-on of sprinkles, yet no topping offer was presented. Although size was specified, the operator could still phrase a compliant large-size confirmation. To improve performance, explicitly offer sprinkles and use proper upsizing language when appropriate while maintaining the charity ask at the end.\", \"gpt_price\": 0, \"video_link\": \"\", \"coupon_used\": 0, \"items_after\": [\"7_1\", \"7_1\"], \"items_upsold\": 0, \"mobile_order\": 0, \"items_initial\": [\"7_1\", \"7_1\"], \"complete_order\": 1, \"asked_more_time\": 0, \"items_addonable\": [\"9003_0\", \"9003_0\"], \"num_items_after\": 2, \"video_file_path\": \"\", \"items_upsellable\": 0, \"items_upsizeable\": 0, \"num_addon_offers\": 0, \"num_addon_success\": 0, \"num_items_initial\": 2, \"num_upsell_offers\": 0, \"num_upsize_offers\": 0, \"reasoning_summary\": \"\", \"num_largest_offers\": 0, \"num_upsell_success\": 0, \"num_upsize_success\": 0, \"out_of_stock_items\": \"0\", \"items_addon_success\": 0, \"items_addon_creators\": [\"7_1\", \"7_1\"], \"items_upsize_success\": 0, \"items_upsize_creators\": 0, \"items_upsold_creators\": 0, \"items_upsizing_creators\": 0, \"num_addon_opportunities\": 2, \"items_upselling_creators\": 0, \"num_upsell_opportunities\": 0, \"num_upsize_opportunities\": 0}",
    items_initial: "[\"7_1\", \"7_1\"]",
    num_items_initial: 2,
    items_after: "[\"7_1\", \"7_1\"]",
    num_items_after: 2,
    num_upsell_opportunities: 0,
    num_upsell_offers: 0,
    num_upsell_success: 0,
    num_largest_offers: 0,
    num_upsize_opportunities: 0,
    num_upsize_offers: 0,
    num_upsize_success: 0,
    num_addon_opportunities: 2,
    num_addon_offers: 0,
    num_addon_success: 0,
    // Weekly totals for display
    weekly_upsell_success: 12,
    weekly_upsize_success: 5,
    weekly_addon_success: 3,
    weekly_upsell_offers: 25,
    weekly_upsize_offers: 15,
    weekly_addon_offers: 10,
    feedback: "The operator correctly entered two small cones and closed the order but made no suggestive-selling attempts. Each cone allowed an add-on of sprinkles, yet no topping offer was presented. Although size was specified, the operator could still phrase a compliant large-size confirmation. To improve performance, explicitly offer sprinkles and use proper upsizing language when appropriate while maintaining the charity ask at the end.",
    issues: "Item information sourced from items.json: Cone (Item ID 7) indicates add-on sprinkles and upsizing to large; Additional Topping list shows Sprinkles (Item ID 9003). No upselling scenarios matched this order. No conflicting instructions encountered.",
    complete_order: 1,
    mobile_order: 0,
    coupon_used: 0,
    asked_more_time: 0,
    out_of_stock_items: "0",
    gpt_price: "50.54",
    reasoning_summary: "",
    video_file_path: "",
    video_link: "",
    score: "0.0",
    upsell_offered_items: null,
    upsize_offered_items: null,
    addon_offered_items: null,
    upsell_candidate_items: null,
    upsize_candidate_items: null,
    addon_candidate_items: null,
    upsell_base_items: null,
    upsize_base_items: null,
    addon_base_items: null,
    upsell_success_items: null,
    upsize_success_items: null,
    addon_success_items: null,
    worker_id: "80b84d5e-59e2-4e3d-af7e-78f2544cbb23",
    begin_time: "2025-08-31 18:45:30+00",
    end_time: "2025-08-31 18:46:15+00",
    employee_name: "Latasha Williams",
    employee_legal_name: "Latasha Williams"
  }
]

interface TopTransactionsHighlightProps {
  locationId: string
  date?: string
  className?: string
}

const getRankBadgeColor = (rank: number) => {
  switch (rank) {
    case 1: return "bg-yellow-100 text-yellow-800 border-yellow-300"
    case 2: return "bg-gray-100 text-gray-800 border-gray-300"
    case 3: return "bg-orange-100 text-orange-800 border-orange-300"
    default: return "bg-blue-100 text-blue-800 border-blue-300"
  }
}

const getRankIcon = (rank: number) => {
  switch (rank) {
    case 1: return <IconTrophy className="h-4 w-4 text-yellow-600" />
    case 2: case 3: return <IconStar className="h-4 w-4" />
    default: return <IconTrendingUp className="h-4 w-4" />
  }
}

// Helper function to calculate success rates from hardcoded data
const calculateSuccessRate = (success: number, offers: number) => {
  if (offers === 0) return 0
  return Math.round((success / offers) * 100)
}

// Helper to aggregate weekly totals across categories
const getWeeklyAggregates = (tx: any) => {
  // Assume 100 opportunities per category when not provided
  const upsell = {
    opportunities: tx.weekly_upsell_opportunities ?? 100,
    offers: tx.weekly_upsell_offers ?? tx.num_upsell_offers ?? 0,
    successes: tx.weekly_upsell_success ?? tx.num_upsell_success ?? 0,
  }
  const upsize = {
    opportunities: tx.weekly_upsize_opportunities ?? 100,
    offers: tx.weekly_upsize_offers ?? tx.num_upsize_offers ?? 0,
    successes: tx.weekly_upsize_success ?? tx.num_upsize_success ?? 0,
  }
  const addon = {
    opportunities: tx.weekly_addon_opportunities ?? 100,
    offers: tx.weekly_addon_offers ?? tx.num_addon_offers ?? 0,
    successes: tx.weekly_addon_success ?? tx.num_addon_success ?? 0,
  }

  const totalOpportunities = upsell.opportunities + upsize.opportunities + addon.opportunities
  const totalOffers = upsell.offers + upsize.offers + addon.offers
  const totalSuccesses = upsell.successes + upsize.successes + addon.successes
  const weeklyTransactions = tx.weekly_transactions ?? tx.num_transactions_week ?? 0

  return { totalOpportunities, totalOffers, totalSuccesses, weeklyTransactions }
}

// Helper function to calculate composite score
const calculateCompositeScore = (transaction: any) => {
  const { totalOpportunities, totalOffers, totalSuccesses } = getWeeklyAggregates(transaction)
  
  // Offer percentage (offers/opportunities) weighted 80%
  const offerRate = totalOpportunities > 0 ? (totalOffers / totalOpportunities) * 100 : 0
  // Conversion percentage (successes/offers) weighted 20%
  const conversionRate = totalOffers > 0 ? (totalSuccesses / totalOffers) * 100 : 0

  const scorePercent = (offerRate * 0.8) + (conversionRate * 0.2) // 0..100
  return scorePercent // keep as 0..100, rendering will append %
}

const HardcodedTransactionCard = ({ transaction, rank }: { transaction: any, rank: number }) => {
  // Parse the begin_time which is in format "2025-08-31 20:00:51+00"
  // Handle cases where begin_time might be undefined
  let formattedTime = "N/A"
  if (transaction.begin_time) {
    const isoTime = transaction.begin_time.replace('+00', 'Z')
    const startTime = new Date(isoTime)
    formattedTime = isNaN(startTime.getTime()) ? "N/A" : format(startTime, "HH:mm")
  }
  const compositeScore = calculateCompositeScore(transaction)
  
  const upsellingRate = calculateSuccessRate(transaction.num_upsell_success, transaction.num_upsell_offers)
  const upsizingRate = calculateSuccessRate(transaction.num_upsize_success, transaction.num_upsize_offers)
  const addonRate = calculateSuccessRate(transaction.num_addon_success, transaction.num_addon_offers)
  
  return (
    <div className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-all duration-200 bg-white h-full flex flex-col">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <Badge className={`${getRankBadgeColor(rank)} font-semibold text-sm px-3 py-1`}>
            <div className="flex items-center space-x-1">
              {getRankIcon(rank)}
              <span>#{rank}</span>
            </div>
          </Badge>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger>
                <div className="text-base font-medium text-gray-900 truncate max-w-40">
                  {transaction.employee_name}
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <p>Employee: {transaction.employee_name}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-green-600">
            {compositeScore.toFixed(1)}
          </div>
          <div className="text-sm text-gray-500">Composite Score</div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="text-center p-2 bg-green-50 rounded-lg">
          <div className="text-xs text-green-800">Offers</div>
          <div className="text-base font-bold text-green-700">
            {transaction.weekly_upsell_offers ?? transaction.num_upsell_offers ?? 0}
          </div>
          <div className="text-xs text-gray-600">Successes</div>
          <div className="text-sm font-semibold text-green-700">
            {transaction.weekly_upsell_success || transaction.num_upsell_success}
          </div>
          <div className="text-sm text-gray-600 mt-1">Upselling</div>
        </div>
        <div className="text-center p-2 bg-blue-50 rounded-lg">
          <div className="text-xs text-blue-800">Offers</div>
          <div className="text-base font-bold text-blue-700">
            {transaction.weekly_upsize_offers ?? transaction.num_upsize_offers ?? 0}
          </div>
          <div className="text-xs text-gray-600">Successes</div>
          <div className="text-sm font-semibold text-blue-700">
            {transaction.weekly_upsize_success || transaction.num_upsize_success}
          </div>
          <div className="text-sm text-gray-600 mt-1">Upsizing</div>
        </div>
        <div className="text-center p-2 bg-purple-50 rounded-lg">
          <div className="text-xs text-purple-800">Offers</div>
          <div className="text-base font-bold text-purple-700">
            {transaction.weekly_addon_offers ?? transaction.num_addon_offers ?? 0}
          </div>
          <div className="text-xs text-gray-600">Successes</div>
          <div className="text-sm font-semibold text-purple-700">
            {transaction.weekly_addon_success || transaction.num_addon_success}
          </div>
          <div className="text-sm text-gray-600 mt-1">Add-ons</div>
        </div>
      </div>

      <div className="flex items-center justify-between text-sm text-gray-500 mb-4">
        <div className="flex items-center space-x-1">
          <IconClock className="h-4 w-4" />
          <span>{formattedTime}</span>
        </div>
        <div className="flex items-center space-x-1">
          {transaction.mobile_order && (
            <Badge variant="outline" className="text-xs">Mobile</Badge>
          )}
          {transaction.coupon_used && (
            <Badge variant="outline" className="text-xs">Coupon</Badge>
          )}
        </div>
      </div>

      {transaction.feedback && (
        <div className="mb-3 text-xs text-gray-600 bg-gray-50 p-2 rounded-lg">
          <div className="truncate" title={transaction.feedback}>
            {transaction.feedback.length > 120 
              ? `${transaction.feedback.substring(0, 120)}...` 
              : transaction.feedback
            }
          </div>
        </div>
      )}

      {/* Transaction Highlight Button */}
      <div className="mt-auto pt-4">
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" className="w-full">
              <IconEye className="h-4 w-4 mr-2" />
              Transaction Highlight
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center space-x-2">
                <Badge className={`${getRankBadgeColor(rank)} font-semibold`}>
                  <div className="flex items-center space-x-1">
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
                  <h3 className="text-lg font-semibold">Performance Metrics</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                      <span className="font-medium">Weekly Upselling Successes</span>
                      <span className="text-lg font-bold text-green-700">{transaction.weekly_upsell_success || transaction.num_upsell_success}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                      <span className="font-medium">Weekly Upsizing Successes</span>
                      <span className="text-lg font-bold text-blue-700">{transaction.weekly_upsize_success || transaction.num_upsize_success}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
                      <span className="font-medium">Weekly Add-ons Successes</span>
                      <span className="text-lg font-bold text-purple-700">{transaction.weekly_addon_success || transaction.num_addon_success}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="font-medium">Composite Score</span>
                      <span className="text-lg font-bold text-gray-700">{compositeScore.toFixed(1)}</span>
                    </div>
                  </div>
                </div>
                
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold">Transaction Stats</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="font-medium">Initial Items</span>
                      <span className="font-bold">{transaction.num_items_initial}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="font-medium">Final Items</span>
                      <span className="font-bold">{transaction.num_items_after}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="font-medium">Upsell Opportunities</span>
                      <span className="font-bold">{transaction.num_upsell_opportunities}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="font-medium">Upsell Offers</span>
                      <span className="font-bold">{transaction.num_upsell_offers}</span>
                    </div>
                    <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <span className="font-medium">Upsell Successes</span>
                      <span className="font-bold text-green-600">{transaction.num_upsell_success}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Composite Score Formula */}
              <div className="bg-blue-50 p-4 rounded-lg">
                <h3 className="text-lg font-semibold mb-3">Composite Score Formula</h3>
                <div className="text-sm space-y-2">
                  <div className="font-mono bg-white p-2 rounded border">
                    Composite Score = (Offer Rate × 80%) + (Conversion Rate × 20%)
                  </div>
                  <div className="text-gray-600">
                    <p><strong>Offer Rate:</strong> {(transaction.num_upsell_offers + transaction.num_upsize_offers + transaction.num_addon_offers) / (transaction.num_upsell_opportunities + transaction.num_upsize_opportunities + transaction.num_addon_opportunities) * 100}%</p>
                    <p><strong>Conversion Rate:</strong> {(transaction.num_upsell_success + transaction.num_upsize_success + transaction.num_addon_success) / (transaction.num_upsell_offers + transaction.num_upsize_offers + transaction.num_addon_offers) * 100}%</p>
                    <p className="font-bold text-lg mt-2">Total: {compositeScore.toFixed(1)}</p>
                  </div>
                </div>
              </div>

              {/* Full Feedback */}
              {transaction.feedback && (
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold">Detailed Feedback</h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <p className="text-sm leading-relaxed">{transaction.feedback}</p>
                  </div>
                </div>
              )}

              {/* Transaction Transcript */}
              {transaction.transcript && (
                <div className="space-y-2">
                  <h3 className="text-lg font-semibold">Transaction Transcript</h3>
                  <div className="bg-gray-50 p-4 rounded-lg max-h-60 overflow-y-auto">
                    <pre className="text-sm whitespace-pre-wrap font-mono">{transaction.transcript}</pre>
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  )
}

export function TopTransactionsHighlight({ locationId, date, className }: TopTransactionsHighlightProps) {
  // Use hardcoded transactions instead of API call
  const transactions = hardcodedTransactions

  // CSV column definitions for hardcoded transactions
  const csvColumns: CSVColumn[] = [
    { key: 'transaction_id', label: 'Transaction ID' },
    { key: 'employee_name', label: 'Employee Name' },
    { key: 'begin_time', label: 'Start Time', transform: formatDateForCSV },
    { key: 'end_time', label: 'End Time', transform: formatDateForCSV },
    { key: 'score', label: 'Base Score' },
    { key: 'num_upsell_opportunities', label: 'Upsell Opportunities' },
    { key: 'num_upsell_offers', label: 'Upsell Offers' },
    { key: 'num_upsell_success', label: 'Upsell Successes' },
    { key: 'num_upsize_opportunities', label: 'Upsize Opportunities' },
    { key: 'num_upsize_offers', label: 'Upsize Offers' },
    { key: 'num_upsize_success', label: 'Upsize Successes' },
    { key: 'num_addon_opportunities', label: 'Addon Opportunities' },
    { key: 'num_addon_offers', label: 'Addon Offers' },
    { key: 'num_addon_success', label: 'Addon Successes' },
    { key: 'items_initial', label: 'Initial Items' },
    { key: 'items_after', label: 'Final Items' },
    { key: 'feedback', label: 'Feedback' },
    { key: 'mobile_order', label: 'Mobile Order' },
    { key: 'coupon_used', label: 'Coupon Used' },
  ];

  const exportTopTransactions = () => {
    if (!transactions.length) return;
    
    const csv = convertToCSV(transactions, csvColumns);
    const timestamp = new Date().toISOString().slice(0, 10);
    const filename = `top_transactions_${locationId}_${date || timestamp}_${new Date().toISOString().slice(0, 19).replace(/[:-]/g, '')}.csv`;
    
    downloadCSV(csv, filename);
  };

  if (!locationId) {
    return null
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <IconTrophy className="h-5 w-5 text-yellow-600" />
              <span>Transactions of the Week</span>
            </CardTitle>
            <CardDescription>AI-powered performance highlights with weekly totals</CardDescription>
          </div>
          <div className="flex items-center space-x-2">
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
                <TooltipTrigger>
                  <IconInfoCircle className="h-5 w-5 text-gray-400 hover:text-gray-600 cursor-help" />
                </TooltipTrigger>
                <TooltipContent className="max-w-sm">
                  <div className="space-y-2">
                    <div className="font-semibold">AI Scoring Algorithm:</div>
                    <div className="text-xs space-y-1">
                      <div>• Base Score: 40%</div>
                      <div>• Upselling: 25%</div>
                      <div>• Upsizing: 20%</div>
                      <div>• Add-ons: 15%</div>
                    </div>
                    <div className="text-xs text-gray-500 pt-1">
                      Showing top 3 performers
                    </div>
                  </div>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {/* Vertically stacked layout, compact rows */}
        <div className="flex flex-col space-y-3">
          <HardcodedTransactionCard transaction={transactions[0]} rank={1} />
          <HardcodedTransactionCard transaction={transactions[1]} rank={2} />
          <HardcodedTransactionCard transaction={transactions[2]} rank={3} />
        </div>
        
        {transactions.length > 0 && (
          <div className="mt-4 pt-3 border-t border-gray-200">
            <div className="text-xs text-gray-500 text-center">
              Showing top 3 transactions of the week with weekly performance totals
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
