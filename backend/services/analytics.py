from services.database import Supa
from datetime import datetime, timedelta
import json

db = Supa()

class Analytics:

    def __init__(self, run_id: str, worker_id=None):
        self.worker_id = worker_id
        self.run_id = run_id
        self.worker_id = worker_id
        self.location_id = db.get_location_from_run(self.run_id)

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
        items = db.get_items(self.location_id)
        item_analytics = {}
        
        # Initialize item structure
        for item in items:
            item_analytics[item["item_id"]] = {
                "name": item["item_name"],
                "sizes": {},
                "transitions": {"1_to_2": 0, "1_to_3": 0, "2_to_3": 0}
            }
        
        # Get transaction data
        if self.worker_id:
            transactions = db.view("graded_rows_filtered").select("*").eq("run_id", self.run_id).eq("worker_id", self.worker_id).execute()
        else:
            transactions = db.view("graded_rows_filtered").select("*").eq("run_id", self.run_id).execute()
        
        for tx in transactions.data:
            self._count_transaction_metrics(tx, item_analytics)
        
        return item_analytics
    
    def _count_transaction_metrics(self, tx, item_analytics):
        """Count metrics for a single transaction"""
        # Parse JSON arrays from transaction
        upsell_base = self._parse_json_array(tx.get("upsell_base_items", "0"))
        upsell_candidates = self._parse_json_array(tx.get("upsell_candidate_items", "0"))
        upsell_offered = self._parse_json_array(tx.get("upsell_offered_items", "0"))
        upsell_success = self._parse_json_array(tx.get("upsell_success_items", "0"))
        upsell_base_sold = self._parse_json_array(tx.get("upsell_base_sold_items", "0"))
        
        upsize_base = self._parse_json_array(tx.get("upsize_base_items", "0"))
        upsize_candidates = self._parse_json_array(tx.get("upsize_candidate_items", "0"))
        upsize_offered = self._parse_json_array(tx.get("upsize_offered_items", "0"))
        upsize_success = self._parse_json_array(tx.get("upsize_success_items", "0"))
        upsize_base_sold = self._parse_json_array(tx.get("upsize_base_sold_items", "0"))
        # Debug: print("Upsize base", upsize_base, "Upsize offered", upsize_offered, "upsize candidates", upsize_candidates, "Upsize success", upsize_success)
        
        addon_base = self._parse_json_array(tx.get("addon_base_items", "0"))
        addon_candidates = self._parse_json_array(tx.get("addon_candidate_items", "0"))
        addon_offered = self._parse_json_array(tx.get("addon_offered_items", "0"))
        addon_success = self._parse_json_array(tx.get("addon_success_items", "0"))
        addon_base_sold = self._parse_json_array(tx.get("addon_base_sold_items", "0"))
        # Count each metric type
        self._count_items(upsell_base, item_analytics, "upsell_base")
        self._count_items(upsell_candidates, item_analytics, "upsell_candidates")
        self._count_items(upsell_offered, item_analytics, "upsell_offered")
        self._count_items(upsell_success, item_analytics, "upsell_success")
        self._count_items(upsell_base_sold, item_analytics, "upsell_base_sold")
        self._count_items(upsize_base, item_analytics, "upsize_base")
        self._count_items(upsize_candidates, item_analytics, "upsize_candidates")
        self._count_items(upsize_offered, item_analytics, "upsize_offered")
        self._count_items(upsize_success, item_analytics, "upsize_success")
        self._count_items(upsize_base_sold, item_analytics, "upsize_base_sold")
        self._count_items(addon_base, item_analytics, "addon_base")
        self._count_items(addon_candidates, item_analytics, "addon_candidates")
        self._count_items(addon_offered, item_analytics, "addon_offered")
        self._count_items(addon_success, item_analytics, "addon_success")
        self._count_items(addon_base_sold, item_analytics, "addon_base_sold_items")
        # Track size transitions
        self._track_transitions(upsize_base, upsize_success, item_analytics)
    
    def _parse_json_array(self, json_str):
        """Parse JSON array string to list"""
        if json_str == "0" or not json_str:
            return []
        try:
            return json.loads(json_str) if isinstance(json_str, str) else json_str
        except:
            return []
    
    def _count_items(self, items, item_analytics, metric_type):
        """Count items for a specific metric type"""
        for item in items:
            item_id, size = int(item.split("_")[0]), item.split("_")[1]  # Keep size as string
            # Debug: print(f"Processing item {item} -> item_id: {item_id}, size: {size}, metric_type: {metric_type}")
            if item_id in item_analytics:
                if size not in item_analytics[item_id]["sizes"]:
                    item_analytics[item_id]["sizes"][size] = {
                        "upsell_base": 0, "upsell_candidates": 0, "upsell_offered": 0, "upsell_success": 0, "upsell_base_sold": 0,
                        "upsize_base": 0, "upsize_candidates": 0, "upsize_offered": 0, "upsize_success": 0, "upsize_base_sold": 0,
                        "addon_base": 0, "addon_candidates": 0, "addon_offered": 0, "addon_success": 0, "addon_base_sold_items": 0
                    }
                item_analytics[item_id]["sizes"][size][metric_type] += 1
                # Debug: print(f"Incremented {metric_type} for item {item_id}, size {size}. New count: {item_analytics[item_id]['sizes'][size][metric_type]}")
            # else:
                # Debug: print(f"Item ID {item_id} not found in item_analytics")
    
    def _track_transitions(self, upsize_base_items, upsize_success_items, item_analytics):
        """Track size transitions for successful upsizes"""
        for success_item in upsize_success_items:
            success_item_id, success_size = success_item.split("_")
            success_item_id = int(success_item_id)  # Convert to int for lookup
            
            # Find the corresponding base item for this success item
            for base_item in upsize_base_items:
                base_item_id, base_size = base_item.split("_")
                base_item_id = int(base_item_id)  # Convert to int for lookup
                
                # If same item but different size, this is our transition
                if base_item_id == success_item_id and base_size != success_size:
                    if success_item_id in item_analytics:
                        transition_key = f"{base_size}_to_{success_size}"
                        if transition_key in item_analytics[success_item_id]["transitions"]:
                            item_analytics[success_item_id]["transitions"][transition_key] += 1
                    break
    
    def generate_analytics_json(self):
        """Generate complete analytics JSON that fits the database schema"""
        # Calculate all metrics
        total_transactions = self.get_total_transactions()
        complete_transactions = self.get_complete_transactions()
        completion_rate = self.get_completion_rate() if total_transactions > 0 else 0
        
        avg_items_initial = self.avg_items_initial_order()
        avg_items_final = self.avg_items_after_order()
        avg_item_increase = avg_items_final - avg_items_initial
        
        # Upsell metrics
        upsell_opportunities = self.get_total_upsell_opportunities()
        upsell_offers = self.get_total_upsell_offers()
        upsell_successes = self.get_total_upsell_success()
        upsell_conversion_rate = upsell_successes / upsell_offers if upsell_offers > 0 else 0
        upsell_revenue = 0  # TODO: Calculate based on item prices
        
        # Upsize metrics
        upsize_opportunities = self.get_total_upsize_opportunities()
        upsize_offers = self.get_total_upsize_offers()
        upsize_successes = self.get_total_upsize_success()
        upsize_conversion_rate = upsize_successes / upsize_offers if upsize_offers > 0 else 0
        upsize_revenue = 0  # TODO: Calculate based on size upgrade prices
        
        # Addon metrics
        addon_opportunities = self.get_total_addon_opportunities()
        addon_offers = self.get_total_addon_offers()
        addon_successes = self.get_total_addon_success()
        addon_conversion_rate = addon_successes / addon_offers if addon_offers > 0 else 0
        addon_revenue = 0  # TODO: Calculate based on addon prices
        
        # Overall metrics
        total_opportunities = upsell_opportunities + upsize_opportunities + addon_opportunities
        total_offers = upsell_offers + upsize_offers + addon_offers
        total_successes = upsell_successes + upsize_successes + addon_successes
        overall_conversion_rate = total_successes / total_offers if total_offers > 0 else 0
        total_revenue = upsell_revenue + upsize_revenue + addon_revenue
        
        # Get detailed item analytics
        item_analytics = self.get_item_analytics()
        
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
            "upsell_revenue": upsell_revenue,
            "upsize_opportunities": upsize_opportunities,
            "upsize_offers": upsize_offers,
            "upsize_successes": upsize_successes,
            "upsize_conversion_rate": round(upsize_conversion_rate, 4),
            "upsize_revenue": upsize_revenue,
            "addon_opportunities": addon_opportunities,
            "addon_offers": addon_offers,
            "addon_successes": addon_successes,
            "addon_conversion_rate": round(addon_conversion_rate, 4),
            "addon_revenue": addon_revenue,
            "total_opportunities": total_opportunities,
            "total_offers": total_offers,
            "total_successes": total_successes,
            "overall_conversion_rate": round(overall_conversion_rate, 4),
            "total_revenue": total_revenue,
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