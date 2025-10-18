from services.database import Supa
from datetime import datetime, timedelta
import json
import time

db = Supa()

class Analytics:

    def __init__(self, run_id: str, worker_id=None):
        self.worker_id = worker_id
        self.run_id = run_id
        self.worker_id = worker_id
        self.location_id = db.get_location_from_run(self.run_id)
        self.item_performance = {}  # New structure for detailed item analytics
        self.revenue_map = {} 
        self.upsell_revenue = 0
        self.upsize_revenue = 0
        self.addon_revenue = 0

    def get_total_transactions(self):
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("*").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("*").eq("run_id", self.run_id).execute()
        return len(result.data) if result.data else 0
    
    def get_complete_transactions(self):
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("*").eq("run_id", self.run_id).eq("complete_order", 1).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("*").eq("run_id", self.run_id).eq("complete_order", 1).execute()
        return len(result.data) if result.data else 0

    def get_completion_rate(self):
        return self.get_complete_transactions() / self.get_total_transactions()

    def avg_items_initial_order(self):
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("items_initial").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("items_initial").eq("run_id", self.run_id).execute()
        return sum(len(row["items_initial"]) for row in result.data) / len(result.data) if result.data else 0
    
    def avg_items_after_order(self):
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("items_after").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("items_after").eq("run_id", self.run_id).execute()
        return sum(len(row["items_after"]) for row in result.data) / len(result.data) if result.data else 0

    def get_total_upsell_opportunities(self): 
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("num_upsell_opportunities").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("num_upsell_opportunities").eq("run_id", self.run_id).execute()
        return sum(row["num_upsell_opportunities"] for row in result.data) if result.data else 0

    def get_total_upsell_offers(self): 
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("num_upsell_offers").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("num_upsell_offers").eq("run_id", self.run_id).execute()
        return sum(row["num_upsell_offers"] for row in result.data) if result.data else 0
    
    def get_total_upsell_success(self): 
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("num_upsell_success").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("num_upsell_success").eq("run_id", self.run_id).execute()
        return sum(row["num_upsell_success"] for row in result.data) if result.data else 0
    
    def get_total_upsize_opportunities(self): 
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("num_upsize_opportunities").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("num_upsize_opportunities").eq("run_id", self.run_id).execute()
        return sum(row["num_upsize_opportunities"] for row in result.data) if result.data else 0
    
    def get_total_upsize_offers(self): 
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("num_upsize_offers").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("num_upsize_offers").eq("run_id", self.run_id).execute()
        return sum(row["num_upsize_offers"] for row in result.data) if result.data else 0
    
    def get_total_upsize_success(self): 
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("num_upsize_success").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("num_upsize_success").eq("run_id", self.run_id).execute()
        return sum(row["num_upsize_success"] for row in result.data) if result.data else 0
   
    def get_total_addon_opportunities(self): 
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("num_addon_opportunities").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("num_addon_opportunities").eq("run_id", self.run_id).execute()
        return sum(row["num_addon_opportunities"] for row in result.data) if result.data else 0

    def get_total_addon_offers(self): 
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("num_addon_offers").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("num_addon_offers").eq("run_id", self.run_id).execute()
        return sum(row["num_addon_offers"] for row in result.data) if result.data else 0
    
    def get_total_addon_success(self): 
        if self.worker_id:
            result = db.view("graded_rows_filtered").select("num_addon_success").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("num_addon_success").eq("run_id", self.run_id).execute()
        return sum(row["num_addon_success"] for row in result.data) if result.data else 0

    def get_item_analytics(self):
        """Get item-level analytics with size tracking"""
        print("🔍 DEBUG: Starting get_item_analytics...")
        start_time = time.time()
        
        # Check if we already have data to avoid reprocessing
        if hasattr(self, 'item_performance') and self.item_performance and hasattr(self, 'revenue_map') and self.revenue_map:
            print("🔍 DEBUG: Item analytics already processed, returning cached data")
            return self.item_performance, self.revenue_map
        
        # Reset performance tracking
        self.item_performance = {}
        self.revenue_map = {}
        
        # Get transaction data
        print("🔍 DEBUG: Getting transaction data from database...")
        tx_start = time.time()
        if self.worker_id:
            transactions = db.view("graded_rows_filtered").select("*").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            transactions = db.view("graded_rows_filtered").select("*").eq("run_id", self.run_id).execute()
        print(f"🔍 DEBUG: Got {len(transactions.data)} transactions in {time.time() - tx_start:.2f}s")
        
        # Get price data once for all transactions
        print("🔍 DEBUG: Getting price data once for all transactions...")
        price_start = time.time()
        items_prices = db.get_items_prices(self.location_id)
        meals_prices = db.get_meals_prices(self.location_id)
        addons_prices = db.get_addons_prices(self.location_id)
        print(f"🔍 DEBUG: Addons prices: {addons_prices}")
        print(f"🔍 DEBUG: Got price data in {time.time() - price_start:.2f}s (items: {len(items_prices)}, meals: {len(meals_prices)}, addons: {len(addons_prices)})")
        
        print("🔍 DEBUG: Processing transactions...")
        process_start = time.time()
        for i, tx in enumerate(transactions.data):
            if i % 10 == 0:  # Log every 10 transactions
                print(f"🔍 DEBUG: Processing transaction {i+1}/{len(transactions.data)}")
            self._count_transaction_metrics(tx, items_prices, meals_prices, addons_prices)
        print(f"🔍 DEBUG: Processed all transactions in {time.time() - process_start:.2f}s")
        
        total_time = time.time() - start_time
        print(f"🔍 DEBUG: get_item_analytics completed in {total_time:.2f}s")
        return self.item_performance, self.revenue_map
        
    
    def _count_transaction_metrics(self, tx, items_prices, meals_prices, addons_prices):
        """Count metrics for a single transaction using new relationship map format"""
        # Parse the new relationship maps
        upsell_opportunities = self._parse_json_map(tx.get("upsell_opportunities", "0"))
        upsell_offers = self._parse_json_map(tx.get("upsell_offers", "0"))
        upsell_successes = self._parse_json_map(tx.get("upsell_successes", "0"))
        print(f"🔍 DEBUG: Upsell successes: {upsell_successes}")
        
        upsize_opportunities = self._parse_json_map(tx.get("upsize_opportunities", "0"))
        upsize_offers = self._parse_json_map(tx.get("upsize_offers", "0"))
        upsize_successes = self._parse_json_map(tx.get("upsize_successes", "0"))
        print(f"🔍 DEBUG: Upsize successes: {upsize_successes}")
        addon_opportunities = self._parse_json_map(tx.get("addon_opportunities", "0"))
        addon_offers = self._parse_json_map(tx.get("addon_offers", "0"))
        addon_successes = self._parse_json_map(tx.get("addon_successes", "0"))
        print(f"🔍 DEBUG: Addon successes: {addon_successes}")
        # Process each category using the generic method
        self._process_category_metrics(upsell_opportunities, upsell_offers, upsell_successes, "upsell", items_prices, meals_prices, addons_prices)
        self._process_category_metrics(upsize_opportunities, upsize_offers, upsize_successes, "upsize", items_prices, meals_prices, addons_prices)
        self._process_category_metrics(addon_opportunities, addon_offers, addon_successes, "addon", items_prices, meals_prices, addons_prices)
        

    def _parse_json_map(self, json_str):
        """Parse JSON map string to dictionary"""
        if json_str == "0" or not json_str:
            return {}
        try:
            return json.loads(json_str) if isinstance(json_str, str) else json_str
        except:
            return {}
    
    def _process_category_metrics(self, opportunities, offers, successes, category, items_prices, meals_prices, addons_prices):
        """Generic method to process metrics for any category (upsell/upsize/addon)"""
        
        # Process opportunities
        for main_item_id, target_items in opportunities.items():
            if main_item_id not in self.item_performance:
                self.item_performance[main_item_id] = {
                    "upsell": {"opportunities": 0, "offers": 0, "conversions": 0, "items_count": {}},
                    "upsize": {"opportunities": 0, "offers": 0, "conversions": 0, "items_count": {}},
                    "addon": {"opportunities": 0, "offers": 0, "conversions": 0, "items_count": {}}
                }
            
            # Count opportunities
            self.item_performance[main_item_id][category]["opportunities"] += len(target_items)
            
            # Count individual target items
            for target_item in target_items:
                if target_item not in self.item_performance[main_item_id][category]["items_count"]:
                    self.item_performance[main_item_id][category]["items_count"][target_item] = {
                        "opportunities": 0, "offers": 0, "conversions": 0
                    }
                self.item_performance[main_item_id][category]["items_count"][target_item]["opportunities"] += 1
        
        # Process offers
        for main_item_id, target_items in offers.items():
            if main_item_id in self.item_performance:
                self.item_performance[main_item_id][category]["offers"] += len(target_items)
                for target_item in target_items:
                    if target_item in self.item_performance[main_item_id][category]["items_count"]:
                        self.item_performance[main_item_id][category]["items_count"][target_item]["offers"] += 1
        
        # Process successes and calculate revenue
        print(f"🔍 DEBUG: Processing successes: {successes.items()}")
        for main_item_id, target_items in successes.items():
            if main_item_id in self.item_performance:
                self.item_performance[main_item_id][category]["conversions"] += len(target_items)
                for target_item in target_items:
                    if target_item in self.item_performance[main_item_id][category]["items_count"]:
                        self.item_performance[main_item_id][category]["items_count"][target_item]["conversions"] += 1
                        
                        # Calculate revenue for this success
                        print(f"🔍 DEBUG: Calculating revenue for {category} success: {target_item}")
                        revenue = self._calculate_item_revenue(
                            main_item_id, target_item, category, 
                            items_prices, meals_prices, addons_prices
                        )
                        
                        # Add to revenue map
                        if target_item not in self.revenue_map:
                            self.revenue_map[target_item] = 0
                        self.revenue_map[target_item] += revenue
    
    def _calculate_item_revenue(self, main_item_id, target_item, category, items_prices, meals_prices, addons_prices):
        """Calculate revenue generated by a specific item conversion"""
        if category == "upsell":
            # For upsell, revenue is the full price of the target item
            self.upsell_revenue += meals_prices.get(target_item, items_prices.get(target_item, addons_prices.get(target_item, 0)))
            return meals_prices.get(target_item, items_prices.get(target_item, addons_prices.get(target_item, 0)))
        
        elif category == "upsize":
            # For upsize, revenue is the price difference between target and original
            target_price = meals_prices.get(target_item, items_prices.get(target_item, 0))
            original_price = meals_prices.get(main_item_id, items_prices.get(main_item_id, 0))
            self.upsize_revenue += max(0, target_price - original_price)
            return max(0, target_price - original_price)

        print(f"🔍 DEBUG: Category: {category}, Target item: {target_item}, Main item ID: {main_item_id}")      
        
        if category == "addon":
            # For addon, revenue is the full price of the topping/addon
            price = addons_prices.get(target_item, items_prices.get(target_item, meals_prices.get(target_item, 0)))
            self.addon_revenue += price
            print(f"🔍 DEBUG: Addon price: {price}")
            return price
    
    
    def get_revenue_by_item(self):
        """Get total revenue generated by each item"""
        return self.revenue_map
    
    def get_top_revenue_items(self, limit=10):
        """Get the top revenue-generating items"""
        sorted_items = sorted(self.revenue_map.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:limit]
    
    def get_total_revenue(self):
        """Get total revenue across all items"""
        return sum(self.revenue_map.values())
    
    def get_item_performance_summary(self):
        """Get summary of item performance across all categories"""
        return self.item_performance
    
    def get_best_performing_combinations(self, category="upsell", min_offers=1):
        """Get the best performing item combinations for a specific category"""
        best_combinations = []
        
        for main_item, data in self.item_performance.items():
            if category in data:
                for target_item, counts in data[category]["items_count"].items():
                    if counts["offers"] >= min_offers:
                        conversion_rate = counts["conversions"] / counts["offers"]
                        best_combinations.append({
                            "main_item": main_item,
                            "target_item": target_item,
                            "conversion_rate": round(conversion_rate, 4),
                            "total_conversions": counts["conversions"],
                            "total_offers": counts["offers"],
                            "total_opportunities": counts["opportunities"]
                        })
        
        # Sort by conversion rate, then by total conversions
        best_combinations.sort(key=lambda x: (x["conversion_rate"], x["total_conversions"]), reverse=True)
        return best_combinations
    
    def get_item_total_performance(self, item_id):
        """Get total performance across all categories for a specific item"""
        if item_id not in self.item_performance:
            return None
        
        data = self.item_performance[item_id]
        return {
            "item_id": item_id,
            "total_opportunities": (
                data["upsell"]["opportunities"] + 
                data["upsize"]["opportunities"] + 
                data["addon"]["opportunities"]
            ),
            "total_offers": (
                data["upsell"]["offers"] + 
                data["upsize"]["offers"] + 
                data["addon"]["offers"]
            ),
            "total_conversions": (
                data["upsell"]["conversions"] + 
                data["upsize"]["conversions"] + 
                data["addon"]["conversions"]
            ),
            "upsell_rate": data["upsell"]["conversions"] / max(data["upsell"]["offers"], 1),
            "upsize_rate": data["upsize"]["conversions"] / max(data["upsize"]["offers"], 1),
            "addon_rate": data["addon"]["conversions"] / max(data["addon"]["offers"], 1),
            "overall_rate": (
                data["upsell"]["conversions"] + data["upsize"]["conversions"] + data["addon"]["conversions"]
            ) / max(
                data["upsell"]["offers"] + data["upsize"]["offers"] + data["addon"]["offers"], 1
            )
        }
    
    def get_underperforming_items(self, min_opportunities=5, max_conversion_rate=0.3):
        """Find items with many opportunities but low conversion rates"""
        underperforming = []
        
        for item_id, data in self.item_performance.items():
            total_opportunities = (
                data["upsell"]["opportunities"] + 
                data["upsize"]["opportunities"] + 
                data["addon"]["opportunities"]
            )
            total_conversions = (
                data["upsell"]["conversions"] + 
                data["upsize"]["conversions"] + 
                data["addon"]["conversions"]
            )
            
            if total_opportunities >= min_opportunities:
                conversion_rate = total_conversions / total_opportunities
                if conversion_rate <= max_conversion_rate:
                    underperforming.append({
                        "item_id": item_id,
                        "total_opportunities": total_opportunities,
                        "total_conversions": total_conversions,
                        "conversion_rate": round(conversion_rate, 4),
                        "upsell_opps": data["upsell"]["opportunities"],
                        "upsize_opps": data["upsize"]["opportunities"],
                        "addon_opps": data["addon"]["opportunities"]
                    })
        
        # Sort by conversion rate (lowest first)
        underperforming.sort(key=lambda x: x["conversion_rate"])
        return underperforming

    def generate_analytics_json(self):
        """Generate complete analytics JSON that fits the database schema"""
        print("🔍 DEBUG: Starting generate_analytics_json...")
        start_time = time.time()
        
        # Calculate all metrics
        print("🔍 DEBUG: Getting basic metrics...")
        basic_start = time.time()
        total_transactions = self.get_total_transactions()
        complete_transactions = self.get_complete_transactions()
        completion_rate = self.get_completion_rate() if total_transactions > 0 else 0
        
        avg_items_initial = self.avg_items_initial_order()
        avg_items_final = self.avg_items_after_order()
        avg_item_increase = avg_items_final - avg_items_initial
        print(f"🔍 DEBUG: Got basic metrics in {time.time() - basic_start:.2f}s")
        
        # Get detailed item analytics first (this populates item_performance and revenue_map)
        print("🔍 DEBUG: Getting detailed item analytics...")
        item_start = time.time()
        item_analytics = self.get_item_analytics()
        print(f"🔍 DEBUG: Got item analytics in {time.time() - item_start:.2f}s")
        
        # Calculate metrics from the new structure
        print("🔍 DEBUG: Calculating metrics from new structure...")
        calc_start = time.time()
        
        # Initialize totals
        upsell_opportunities = upsell_offers = upsell_successes = 0
        upsize_opportunities = upsize_offers = upsize_successes = 0
        addon_opportunities = addon_offers = addon_successes = 0

        # Sum up from item_performance
        for item_id, data in self.item_performance.items():
            upsell_opportunities += data["upsell"]["opportunities"]
            upsell_offers += data["upsell"]["offers"]
            upsell_successes += data["upsell"]["conversions"]

            upsize_opportunities += data["upsize"]["opportunities"]
            upsize_offers += data["upsize"]["offers"]
            upsize_successes += data["upsize"]["conversions"]
            
            addon_opportunities += data["addon"]["opportunities"]
            addon_offers += data["addon"]["offers"]
            addon_successes += data["addon"]["conversions"]
        
        # Calculate conversion rates
        upsell_conversion_rate = upsell_successes / upsell_offers if upsell_offers > 0 else 0
        upsize_conversion_rate = upsize_successes / upsize_offers if upsize_offers > 0 else 0
        addon_conversion_rate = addon_successes / addon_offers if addon_offers > 0 else 0
        
        # Get revenue from revenue_map
        total_revenue = self.get_total_revenue()
        
        # Overall metrics
        total_opportunities = upsell_opportunities + upsize_opportunities + addon_opportunities
        total_offers = upsell_offers + upsize_offers + addon_offers
        total_successes = upsell_successes + upsize_successes + addon_successes
        overall_conversion_rate = total_successes / total_offers if total_offers > 0 else 0
        
        print(f"🔍 DEBUG: Calculated metrics in {time.time() - calc_start:.2f}s")
        
        # Create the analytics JSON structure
        analytics_data = {
            "run_id": self.run_id,
            "total_transactions": total_transactions,
            "complete_transactions": complete_transactions,
            "completion_rate": round(completion_rate, 4),
            "avg_items_initial": round(avg_items_initial, 2),
            "avg_items_final": round(avg_items_final, 2),
            "avg_item_increase": round(avg_item_increase, 2),
            "upsell_opportunities": upsell_opportunities,
            "upsell_offers": upsell_offers,
            "upsell_successes": upsell_successes,
            "upsell_conversion_rate": round(upsell_conversion_rate, 4),
            "upsell_revenue": self.upsell_revenue,
            "upsize_opportunities": upsize_opportunities,
            "upsize_offers": upsize_offers,
            "upsize_successes": upsize_successes,
            "upsize_conversion_rate": round(upsize_conversion_rate, 4),
            "upsize_revenue": self.upsize_revenue,
            "addon_opportunities": addon_opportunities,
            "addon_offers": addon_offers,
            "addon_successes": addon_successes,
            "addon_conversion_rate": round(addon_conversion_rate, 4),
            "addon_revenue": self.addon_revenue,
            "total_opportunities": total_opportunities,
            "total_offers": total_offers,
            "total_successes": total_successes,
            "overall_conversion_rate": round(overall_conversion_rate, 4),
            "total_revenue": total_revenue,
            "detailed_revenue": json.dumps(self.revenue_map),
            "detailed_analytics": json.dumps(item_analytics)
        }
        
        return analytics_data

    def generate_analytics_over_time(self, start_date=None, end_date=None): 
        """Generate analytics over time"""
        
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get run analytics data with run information
        run_analytics = db.view("run_analytics").select("""
            *,
            runs!inner(run_date, location_id, org_id),
            locations!inner(name),
            organizations!inner(name)
        """).gte("runs.run_date", start_date).lte("runs.run_date", end_date).execute()
        
        # Create mapping structure
        analytics_map = {}
        
        for analytics_row in run_analytics.data:
            run_date = analytics_row['runs']['run_date']
            
            if run_date not in analytics_map:
                analytics_map[run_date] = {
                    'upsell': {
                        'opportunities': 0,
                        'offers': 0,
                        'successes': 0
                    },
                    'upsize': {
                        'opportunities': 0,
                        'offers': 0,
                        'successes': 0
                    },
                    'addon': {
                        'opportunities': 0,
                        'offers': 0,
                        'successes': 0
                    },
                    'location_name': analytics_row['locations']['name'],
                    'org_name': analytics_row['organizations']['name']
                }
            
            # Aggregate the metrics
            analytics_map[run_date]['upsell']['opportunities'] += analytics_row.get('upsell_opportunities', 0)
            analytics_map[run_date]['upsell']['offers'] += analytics_row.get('upsell_offers', 0)
            analytics_map[run_date]['upsell']['successes'] += analytics_row.get('upsell_successes', 0)
            
            analytics_map[run_date]['upsize']['opportunities'] += analytics_row.get('upsize_opportunities', 0)
            analytics_map[run_date]['upsize']['offers'] += analytics_row.get('upsize_offers', 0)
            analytics_map[run_date]['upsize']['successes'] += analytics_row.get('upsize_successes', 0)
            
            analytics_map[run_date]['addon']['opportunities'] += analytics_row.get('addon_opportunities', 0)
            analytics_map[run_date]['addon']['offers'] += analytics_row.get('addon_offers', 0)
            analytics_map[run_date]['addon']['successes'] += analytics_row.get('addon_successes', 0)
        
        return analytics_map
    
    def get_analytics_with_conversion_rates(self, start_date=None, end_date=None):
        """Get analytics over time with conversion rates calculated"""
        analytics_map = self.generate_analytics_over_time(start_date, end_date)
        
        # Calculate conversion rates for each date
        for date, data in analytics_map.items():
            # Upsell conversion rate
            if data['upsell']['offers'] > 0:
                data['upsell']['conversion_rate'] = round(
                    data['upsell']['successes'] / data['upsell']['offers'], 4
                )
            else:
                data['upsell']['conversion_rate'] = 0
            
            # Upsize conversion rate
            if data['upsize']['offers'] > 0:
                data['upsize']['conversion_rate'] = round(
                    data['upsize']['successes'] / data['upsize']['offers'], 4
                )
            else:
                data['upsize']['conversion_rate'] = 0
            
            # Addon conversion rate
            if data['addon']['offers'] > 0:
                data['addon']['conversion_rate'] = round(
                    data['addon']['successes'] / data['addon']['offers'], 4
                )
            else:
                data['addon']['conversion_rate'] = 0
        
        return analytics_map
    
    def get_run_analytics(self):
        """Get run analytics from database"""
        if self.run_id and self.worker_id:
            # Get worker-specific analytics for a specific run
            result = db.client.table("run_analytics_worker").select("*").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        elif self.run_id:
            # Get all analytics for a specific run (from main table)
            result = db.client.table("run_analytics").select("*").eq("run_id", self.run_id).execute()
        elif self.worker_id:
            # Get all analytics for a specific worker
            result = db.client.table("run_analytics_worker").select("*").eq("worker_id", self.worker_id).execute()
        else:
            # Get all analytics from main table
            result = db.client.table("run_analytics").select("*").execute()
        
        return result.data if result.data else []
    
    def get_workers_for_run(self):
        """Get all workers that have analytics for a specific run"""
        if self.run_id:
            result = db.view("graded_rows_filtered").select("worker_id, employee_name").eq("run_id", self.run_id).execute()
        else:
            result = db.view("graded_rows_filtered").select("worker_id, employee_name").eq("run_id", self.run_id).execute()
        
        # Get unique workers
        workers = {}
        if result.data:
            for row in result.data:
                worker_id = row.get("worker_id")
                employee_name = row.get("employee_name", "Unknown")
                if worker_id:
                    workers[worker_id] = employee_name
        
        return workers
    
    def upload_to_db(self):
        """Upload analytics to database"""
        analytics_data = self.generate_analytics_json()

        # Insert into appropriate table
        if self.worker_id:
            # Add worker_id to the analytics data for the worker table
            analytics_data["worker_id"] = self.worker_id
            result = db.client.table("run_analytics_worker").insert(analytics_data).execute()
        else:
            result = db.client.table("run_analytics").insert(analytics_data).execute()

        print(f"Uploaded analytics to database for run_id: {self.run_id}, worker_id: {self.worker_id}")
        return result.data