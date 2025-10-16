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
from services.database import Supa
logger = logging.getLogger(__name__)

db = Supa()
class ItemLookupService:
    """Service to lookup item names from IDs using database tables"""
    
    def __init__(self, db: Supa = None, location_id: str = None):
        self.db = db
        self.location_id = "c3607cc3-0f0c-4725-9c42-eb2fdb5e016a"
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
                "*"
            ).eq("location_id", self.location_id).execute()
            
            for item in items_result.data:
                self.items_map[item['item_id']] = {
                    'item_id': item['item_id'],
                    'item_name': item['item_name'],
                    'item_size': item['size'],
                    'price': item.get('price', 0.0)
                }
            
            # Load meals from database
            meals_result = self.db.client.table("meals").select(
                "*"
            ).eq("location_id", self.location_id).execute()
            
            for meal in meals_result.data:
                self.meals_map[meal['item_id']] = {
                    'item_id': meal['item_id'],
                    'item_name': meal['item_name'],
                    'price': meal.get('price', 0.0)
                }
            
            # Load add-ons from database
            addons_result = self.db.client.table("add_ons").select(
                "*"
            ).eq("location_id", self.location_id).execute()
            
            for addon in addons_result.data:
                self.misc_items_map[addon['item_id']] =  {
                    'item_id': addon['item_id'],
                    'item_name': addon['item_name'],
                    'price': addon.get('price', 0.0)
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
            
    def get_full_item_name(self, item: dict) -> str:
        """Get human-readable item name from item code, optionally prefixing a provided size.

        - item_id is the item ID
        """
        if item is None:
            return ""
        # Get the item dat

        print(f"🔍 DEBUG: Got item data: {item}, item_size: {item.get('size')}, item_name: {item.get('item_name')}")

        if item.get("size") and item.get("size") != "None": 
            return item.get("size") + " " + item.get("item_name")
        else:
            return item.get("item_name")
    
    
    
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

    def generate_item_names_map(self):
        """Generate a map of item IDs to item names"""
        item_names_map = {}

        items = db.get_all_item_ids(self.location_id)

        print(f"🔍 DEBUG: Got {len(items)} items")

        for item in items: 
            item_names_map[item['item_id']] = self.get_full_item_name(item)

        return item_names_map