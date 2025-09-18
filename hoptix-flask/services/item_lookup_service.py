#!/usr/bin/env python3
"""
Item Lookup Service for Hoptix Analytics

This service provides item name lookups from item IDs using the menu JSON files.
It maps item codes (like "22_2") to human-readable names (like "Medium Blizzard").
"""

import json
import os
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ItemLookupService:
    """Service to lookup item names from IDs using menu JSON files"""
    
    def __init__(self):
        self.items_map: Dict[int, Dict] = {}
        self.meals_map: Dict[int, Dict] = {}
        self.misc_items_map: Dict[int, Dict] = {}
        self.size_names = {
            0: "",
            1: "Small",
            2: "Medium/Regular", 
            3: "Large"
        }
        self._load_menu_data()
    
    def _load_menu_data(self):
        """Load all menu data from JSON files"""
        try:
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

def get_item_lookup_service() -> ItemLookupService:
    """Get singleton instance of ItemLookupService"""
    global _item_lookup_service
    if _item_lookup_service is None:
        _item_lookup_service = ItemLookupService()
    return _item_lookup_service
