#!/usr/bin/env python3
"""
Item Lookup Service for Hoptix Analytics

This service provides item name lookups from item IDs using the database tables.
It maps item codes (like "22_2") to human-readable names (like "Medium Blizzard").
"""

import json
import os
from typing import Dict, Optional, Tuple
import logging
from integrations.db_supabase import Supa

logger = logging.getLogger(__name__)

class ItemLookupService:
    """Service to lookup item names from IDs using database tables"""
    
    def __init__(self, db: Supa = None, location_id: str = None):
        self.db = db
        self.location_id = location_id
        self.items_map: Dict[int, Dict] = {}
        self.meals_map: Dict[int, Dict] = {}
        self.misc_items_map: Dict[int, Dict] = {}
        self.size_names = {
            0: "",
            1: "Small",
            2: "Medium/Regular", 
            3: "Large"
        }
        
        # Load data from database if available, otherwise fallback to JSON
        if self.db and self.location_id:
            self._load_menu_data_from_db()
        else:
            self._load_menu_data_from_json()
    
    def _load_menu_data_from_db(self):
        """Load all menu data from database tables"""
        try:
            logger.info(f"Loading menu data from database for location {self.location_id}")
            
            # Load items from database
            items_result = self.db.client.table("items").select(
                "item_id, item_name, size_ids, price"
            ).eq("location_id", self.location_id).execute()
            
            for item in items_result.data:
                self.items_map[item['item_id']] = {
                    'Item ID': item['item_id'],
                    'Item': item['item_name'],
                    'Size IDs': item['size_ids'],
                    'Price': item.get('price', 0.0)
                }
            
            # Load meals from database
            meals_result = self.db.client.table("meals").select(
                "item_id, item_name, size_ids, price"
            ).eq("location_id", self.location_id).execute()
            
            for meal in meals_result.data:
                self.meals_map[meal['item_id']] = {
                    'Item ID': meal['item_id'],
                    'Item': meal['item_name'],
                    'Size IDs': meal['size_ids'],
                    'Price': meal.get('price', 0.0)
                }
            
            # Load add-ons from database
            addons_result = self.db.client.table("add_ons").select(
                "item_id, item_name, size_ids, price"
            ).eq("location_id", self.location_id).execute()
            
            for addon in addons_result.data:
                self.misc_items_map[addon['item_id']] =  {
                    'Item ID': addon['item_id'],
                    'Item': addon['item_name'],
                    'Size IDs': addon['size_ids'],
                    'Price': addon.get('price', 0.0)
                }
            
            logger.info(f"Loaded {len(self.items_map)} items, {len(self.meals_map)} meals, {len(self.misc_items_map)} add-ons from database")
            
        except Exception as e:
            logger.error(f"Error loading menu data from database: {e}")
            logger.info("Falling back to JSON files")
            self._load_menu_data_from_json()
    
    def _load_menu_data_from_json(self):
        """Load all menu data from JSON files (fallback)"""
        try:
            logger.info("Loading menu data from JSON files")
            
            # Load items.json
            items_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'items.json')
            with open(items_path, 'r') as f:
                items_data = json.load(f)
                for item in items_data:
                    self.items_map[item['Item ID']] = item
            
            # Load meals.json  
            meals_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'meals.json')
            with open(meals_path, 'r') as f:
                meals_data = json.load(f)
                for meal in meals_data:
                    self.meals_map[meal['Item ID']] = meal
            
            # Load misc_items.json
            misc_path = os.path.join(os.path.dirname(__file__), '..', 'prompts', 'misc_items.json')
            if os.path.exists(misc_path):
                with open(misc_path, 'r') as f:
                    misc_data = json.load(f)
                    for item in misc_data:
                        self.misc_items_map[item['Item ID']] = item
                    
            logger.info(f"Loaded {len(self.items_map)} items, {len(self.meals_map)} meals, {len(self.misc_items_map)} misc items")
            
        except Exception as e:
            logger.error(f"Error loading menu data: {e}")
            
    def parse_item_code(self, item_code: str) -> Tuple[Optional[int], Optional[int]]:
        """Parse item code like '22_2' into (item_id, size_id)"""
        try:
            if '_' in item_code:
                parts = item_code.split('_')
                item_id = int(parts[0])
                size_id = int(parts[1]) if len(parts) > 1 else 0
                return item_id, size_id
            else:
                return int(item_code), 0
        except (ValueError, IndexError):
            return None, None
    
    def get_item_name(self, item_code: str) -> str:
        """Get human-readable item name from item code"""
        item_id, size_id = self.parse_item_code(item_code)
        
        if item_id is None:
            return item_code  # Return original if can't parse
        
        # Check items first
        if item_id in self.items_map:
            item_data = self.items_map[item_id]
            base_name = item_data['Item'].split('[')[0].strip()  # Remove size info in brackets
            size_name = self.size_names.get(size_id, "")
            return f"{size_name} {base_name}".strip()
        
        # Check meals
        if item_id in self.meals_map:
            meal_data = self.meals_map[item_id]
            return meal_data['Item']
        
        # Check misc items
        if item_id in self.misc_items_map:
            misc_data = self.misc_items_map[item_id]
            return misc_data['Item']
        
        # Fallback to original code
        return item_code
    
    def get_item_price(self, item_code: str) -> float:
        """Get item price from item code"""
        item_id, size_id = self.parse_item_code(item_code)
        
        if item_id is None:
            return 0.0
        
        # Check items first
        if item_id in self.items_map:
            item_data = self.items_map[item_id]
            
            # Handle multiple size pricing
            if 'Prices' in item_data:
                return float(item_data['Prices'].get(str(size_id), 0.0))
            # Handle single price
            elif 'Price' in item_data:
                return float(item_data['Price'])
        
        # Check meals
        if item_id in self.meals_map:
            meal_data = self.meals_map[item_id]
            return float(meal_data.get('Price', 0.0))
        
        # Check misc items
        if item_id in self.misc_items_map:
            misc_data = self.misc_items_map[item_id]
            return float(misc_data.get('Price', 0.0))
        
        return 0.0
    
    def get_item_details(self, item_code: str) -> Dict:
        """Get full item details including name, category, etc."""
        item_id, size_id = self.parse_item_code(item_code)
        
        if item_id is None:
            return {"name": item_code, "category": "Unknown", "type": "Unknown"}
        
        # Check items first
        if item_id in self.items_map:
            item_data = self.items_map[item_id]
            base_name = item_data['Item'].split('[')[0].strip()
            size_name = self.size_names.get(size_id, "")
            price = self.get_item_price(f"{item_id}_{size_id}")
            
            return {
                "name": f"{size_name} {base_name}".strip(),
                "base_name": base_name,
                "size": size_name,
                "price": price,
                "category": self._categorize_item(base_name),
                "type": "Item",
                "raw_data": item_data
            }
        
        # Check meals
        if item_id in self.meals_map:
            meal_data = self.meals_map[item_id]
            price = float(meal_data.get('Price', 0.0))
            return {
                "name": meal_data['Item'],
                "base_name": meal_data['Item'],
                "size": "",
                "price": price,
                "category": "Meal",
                "type": "Meal", 
                "raw_data": meal_data
            }
        
        # Check misc items
        if item_id in self.misc_items_map:
            misc_data = self.misc_items_map[item_id]
            price = float(misc_data.get('Price', 0.0))
            return {
                "name": misc_data['Item'],
                "base_name": misc_data['Item'],
                "size": "",
                "price": price,
                "category": "Add-on",
                "type": "Misc",
                "raw_data": misc_data
            }
        
        return {"name": item_code, "category": "Unknown", "type": "Unknown"}
    
    def _categorize_item(self, item_name: str) -> str:
        """Categorize items for analytics"""
        item_lower = item_name.lower()
        
        if any(word in item_lower for word in ['blizzard', 'sundae', 'cone', 'shake', 'malt']):
            return "Treats"
        elif any(word in item_lower for word in ['burger', 'sandwich', 'hot dog', 'chicken']):
            return "Entrees"
        elif any(word in item_lower for word in ['fries', 'onion ring', 'cheese curd']):
            return "Sides"
        elif any(word in item_lower for word in ['drink', 'coke', 'sprite', 'tea', 'coffee']):
            return "Beverages"
        else:
            return "Other"
    
    def enhance_analytics_data(self, analytics_data: Dict) -> Dict:
        """Enhance analytics data by replacing item codes with names"""
        enhanced_data = analytics_data.copy()
        
        # Helper function to enhance item breakdown sections
        def enhance_item_breakdown(item_breakdown: Dict) -> Dict:
            enhanced_breakdown = {}
            for item_code, stats in item_breakdown.items():
                item_name = self.get_item_name(item_code)
                enhanced_breakdown[item_name] = stats
            return enhanced_breakdown
        
        # Enhance main analytics sections (legacy format)
        for category in ["upselling", "upsizing", "addons"]:
            if category in enhanced_data and "by_item" in enhanced_data[category]:
                enhanced_data[category]["by_item"] = enhance_item_breakdown(
                    enhanced_data[category]["by_item"]
                )
        
        # Enhance operator analytics (legacy format)
        if "operator_analytics" in enhanced_data:
            for category in ["upselling", "upsizing", "addons"]:
                if category in enhanced_data["operator_analytics"]:
                    for operator, operator_data in enhanced_data["operator_analytics"][category].items():
                        if "by_item" in operator_data:
                            enhanced_data["operator_analytics"][category][operator]["by_item"] = enhance_item_breakdown(
                                operator_data["by_item"]
                            )
        
        # Enhance store analytics (new structured format)
        if "store" in enhanced_data:
            store_data = enhanced_data["store"]
            
            # Enhance store-level item breakdowns
            for category in ["upselling", "upsizing", "addons"]:
                if category in store_data and "item_breakdown" in store_data[category]:
                    store_data[category]["item_breakdown"] = enhance_item_breakdown(
                        store_data[category]["item_breakdown"]
                    )
            
            # Enhance operator-level item breakdowns
            if "operators" in store_data:
                for operator_name, operator_data in store_data["operators"].items():
                    for category in ["upselling", "upsizing", "addons"]:
                        if category in operator_data and "item_breakdown" in operator_data[category]:
                            operator_data[category]["item_breakdown"] = enhance_item_breakdown(
                                operator_data[category]["item_breakdown"]
                            )
        
        # Enhance top performing items
        if "top_performing_items" in enhanced_data:
            top_items = enhanced_data["top_performing_items"]
            
            for category in ["most_frequent_items", "highest_success_rate_items", "most_successful_items"]:
                if category in top_items:
                    enhanced_category = {}
                    for item_code, stats in top_items[category].items():
                        item_name = self.get_item_name(item_code)
                        enhanced_category[item_name] = stats
                    enhanced_data["top_performing_items"][category] = enhanced_category
        
        return enhanced_data

# Global instance
_item_lookup_service = None

def get_item_lookup_service(db=None, location_id=None) -> ItemLookupService:
    """Get instance of ItemLookupService with optional database connection"""
    # Create a new instance each time to handle different locations
    # In production, you might want to cache these by location_id
    return ItemLookupService(db, location_id)
