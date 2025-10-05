from services.database import Supa
import json

db = Supa()

class Analytics:

    def __init__(self, run_id: str):
        self.run_id = run_id


    def get_total_upsell_opportunities(self): 
        result = db.view("graded_rows_filtered").select("num_upsell_opportunities").eq("run_id", self.run_id).execute()
        return sum(row["num_upsell_opportunities"] for row in result.data) if result.data else 0

    def get_total_upsell_offers(self): 
        result = db.view("graded_rows_filtered").select("num_upsell_offers").eq("run_id", self.run_id).execute()
        return sum(row["num_upsell_offers"] for row in result.data) if result.data else 0
    
    def get_total_upsell_success(self): 
        result = db.view("graded_rows_filtered").select("num_upsell_success").eq("run_id", self.run_id).execute()
        return sum(row["num_upsell_success"] for row in result.data) if result.data else 0
    
    def get_total_upsize_opportunities(self): 
        result = db.view("graded_rows_filtered").select("num_upsize_opportunities").eq("run_id", self.run_id).execute()
        return sum(row["num_upsize_opportunities"] for row in result.data) if result.data else 0

    def get_total_upsize_offers(self): 
        result = db.view("graded_rows_filtered").select("num_upsize_offers").eq("run_id", self.run_id).execute()
        return sum(row["num_upsize_offers"] for row in result.data) if result.data else 0
    
    def get_total_upsize_success(self): 
        result = db.view("graded_rows_filtered").select("num_upsize_success").eq("run_id", self.run_id).execute()
        return sum(row["num_upsize_success"] for row in result.data) if result.data else 0
   
    def get_total_addon_opportunities(self): 
        result = db.view("graded_rows_filtered").select("num_addon_opportunities").eq("run_id", self.run_id).execute()
        return sum(row["num_addon_opportunities"] for row in result.data) if result.data else 0

    def get_total_addon_offers(self): 
        result = db.view("graded_rows_filtered").select("num_addon_offers").eq("run_id", self.run_id).execute()
        return sum(row["num_addon_offers"] for row in result.data) if result.data else 0
    
    def get_total_addon_success(self): 
        result = db.view("graded_rows_filtered").select("num_addon_success").eq("run_id", self.run_id).execute()
        return sum(row["num_addon_success"] for row in result.data) if result.data else 0

    def get_item_analytics(self):
        """Get item-level analytics with size tracking"""
        items = db.get_items()
        item_analytics = {}
        
        # Initialize item structure
        for item in items:
            item_analytics[item["item_id"]] = {
                "name": item["item_name"],
                "sizes": {},
                "transitions": {"1_to_2": 0, "1_to_3": 0, "2_to_3": 0}
            }
        
        # Get transaction data
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
        
        upsize_base = self._parse_json_array(tx.get("upsize_base_items", "0"))
        upsize_candidates = self._parse_json_array(tx.get("upsize_candidate_items", "0"))
        upsize_offered = self._parse_json_array(tx.get("upsize_offered_items", "0"))
        upsize_success = self._parse_json_array(tx.get("upsize_success_items", "0"))

        print("Upsize base", upsize_base, "Upsize offered", upsize_offered, "upsize candidates", upsize_candidates, "Upsize success", upsize_success)
        
        addon_base = self._parse_json_array(tx.get("addon_base_items", "0"))
        addon_candidates = self._parse_json_array(tx.get("addon_candidate_items", "0"))
        addon_offered = self._parse_json_array(tx.get("addon_offered_items", "0"))
        addon_success = self._parse_json_array(tx.get("addon_success_items", "0"))
                
        # Count each metric type
        self._count_items(upsell_base, item_analytics, "upsell_base")
        self._count_items(upsell_candidates, item_analytics, "upsell_candidates")
        self._count_items(upsell_offered, item_analytics, "upsell_offered")
        self._count_items(upsell_success, item_analytics, "upsell_success")
        
        self._count_items(upsize_base, item_analytics, "upsize_base")
        self._count_items(upsize_candidates, item_analytics, "upsize_candidates")
        self._count_items(upsize_offered, item_analytics, "upsize_offered")
        self._count_items(upsize_success, item_analytics, "upsize_success")
        
        self._count_items(addon_base, item_analytics, "addon_base")
        self._count_items(addon_candidates, item_analytics, "addon_candidates")
        self._count_items(addon_offered, item_analytics, "addon_offered")
        self._count_items(addon_success, item_analytics, "addon_success")
        
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
            item_id, size = int(item.split("_")[0]), int(item.split("_")[1])
            if item_id in item_analytics:
                if size not in item_analytics[item_id]["sizes"]:
                    item_analytics[item_id]["sizes"][size] = {
                        "upsell_base": 0, "upsell_candidates": 0, "upsell_offered": 0, "upsell_success": 0,
                        "upsize_base": 0, "upsize_candidates": 0, "upsize_offered": 0, "upsize_success": 0,
                        "addon_base": 0, "addon_candidates": 0, "addon_offered": 0, "addon_success": 0
                    }
                item_analytics[item_id]["sizes"][size][metric_type] += 1
    
    def _track_transitions(self, upsize_base_items, upsize_success_items, item_analytics):
        """Track size transitions for successful upsizes"""
        for success_item in upsize_success_items:
            success_item_id, success_size = success_item.split("_")
            
            # Find the corresponding base item for this success item
            for base_item in upsize_base_items:
                base_item_id, base_size = base_item.split("_")
                
                # If same item but different size, this is our transition
                if success_item_id == base_item_id and success_size != base_size:
                    if success_item_id in item_analytics:
                        transition_key = f"{base_size}_to_{success_size}"
                        if transition_key in item_analytics[success_item_id]["transitions"]:
                            item_analytics[success_item_id]["transitions"][transition_key] += 1
                    break
    