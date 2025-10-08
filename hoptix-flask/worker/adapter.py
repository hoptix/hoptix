from __future__ import annotations
import os, json, tempfile, contextlib, shutil
from typing import List, Dict, Any
from datetime import datetime, timedelta

import numpy as np
import librosa
from moviepy.editor import VideoFileClip
from openai import OpenAI
from dateutil import parser as dateparse

from config import Settings

_settings = Settings()
client = OpenAI(api_key=_settings.OPENAI_API_KEY)

# ---------- Load menu data from database ----------
def _get_menu_data_from_db(db, location_id: str) -> tuple[list, list, list, list, list]:
    """Fetch menu data from database tables for the given location"""
    try:
        # Get items for this location
        items_result = db.client.table("items").select(
            "item_id, item_name, ordered_cnt, size_ids, upsell, upsize, addon"
        ).eq("location_id", location_id).execute()
        
        # Get meals for this location
        meals_result = db.client.table("meals").select(
            "item_id, item_name, ordered_cnt, inclusions, upsell, upsize, addon, size_ids"
        ).eq("location_id", location_id).execute()
        
        # Get add-ons for this location
        addons_result = db.client.table("add_ons").select(
            "item_id, item_name, size_ids"
        ).eq("location_id", location_id).execute()
        
        # Convert to the format expected by the prompt
        items = []
        for item in items_result.data:
            items.append({
                "Item": item["item_name"],
                "Item ID": item["item_id"],
                "Size IDs": item["size_ids"],
                "Ordered Items Count": item["ordered_cnt"] or 1,
                "Upselling Chance": item["upsell"] or "0",
                "Upsizing Chance": item["upsize"] or "0",
                "Add on Chance": item["addon"] or "0"
            })
        
        meals = []
        for meal in meals_result.data:
            meals.append({
                "Item": meal["item_name"],
                "Item ID": meal["item_id"],
                "Size IDs": meal["size_ids"],
                "Ordered Items Count": meal["ordered_cnt"] or 1,
                "Inclusions": meal["inclusions"] or "",
                "Upselling Chance": meal["upsell"] or "0",
                "Upsizing Chance": meal["upsize"] or "0",
                "Add on Chance": meal["addon"] or "0"
            })
        
        addons = []
        for addon in addons_result.data:
            addons.append({
                "Item": addon["item_name"],
                "Item ID": addon["item_id"],
                "Size IDs": addon["size_ids"]
            })
        
        # For now, keep upselling and upsizing as static (can be moved to DB later if needed)
        upselling = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.UPSELLING_JSON))
        upsizing  = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.UPSIZING_JSON))
        
        print(f"Loaded menu data for location {location_id}: {len(items)} items, {len(meals)} meals, {len(addons)} add-ons")
        
        return upselling, upsizing, addons, items, meals
        
    except Exception as e:
        print(f"Error loading menu data from database: {e}")
        # Fallback to JSON files if database fails
        return _get_menu_data_from_json()

def _read_json_or_empty(path: str) -> list | dict:
    """Fallback function to read JSON files"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _get_menu_data_from_json() -> tuple[list, list, list, list, list]:
    """Fallback to load menu data from JSON files"""
    upselling = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.UPSELLING_JSON))
    upsizing  = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.UPSIZING_JSON))
    addons    = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.ADDONS_JSON))
    items     = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.ITEMS_JSON))
    meals     = _read_json_or_empty(os.path.join(_settings.PROMPTS_DIR, _settings.MEALS_JSON))
    
    print("Using fallback JSON files for menu data")
    return upselling, upsizing, addons, items, meals

def _build_step2_prompt(db=None, location_id: str = None) -> str:
    """Build the step 2 prompt with menu data from database or JSON fallback"""
    if db and location_id:
        upselling, upsizing, addons, items, meals = _get_menu_data_from_db(db, location_id)
    else:
        upselling, upsizing, addons, items, meals = _get_menu_data_from_json()

    print(f"Menu data loaded: {len(upselling)} upselling scenarios, {len(upsizing)} upsizing scenarios, {len(addons)} add-ons, {len(items)} items, {len(meals)} meals")


    template = """
You are a performance reviewer assessing a Dairy Queen drive-thru operator's handling of an order, focusing on recording statistics about orders, upsizing opportunities, and upselling opportunities.

**Definitions**
1. Upselling Opportunity: If a customer's order presented an opportunity to upgrade from a burger to a meal or a combo. Additionally, adding fries, a drink, or both to the order counts as upselling.
2. Upsizing Opportunity: If a customer does not specify a size for a meal or combo or fries or drink ordered, then there is an opportunity to upsize to a large size. Upsizing to a small or medium size does not count. There is no chance to upsize if a size was specified.
3. Extra Topping opportunity: If a customer orders an item that has the option for extra toppingss to be added on. For example ice cream has additional ice-cream toppings as its additional topping.
3. Chance Guide: If the operator's attempt followed a valid upselling or upsizing process in alignment with the scenario.

**Upselling Scenarios**:
<<UPSELLING_JSON>>

**Note**: If a customer uses a coupon on a specific item in an order, then that item has 0 upselling chances, but the rest of the items in the order do have their usual upselling chances. If a customer orders 2 Cheeseburgers, but has a coupon for one of them, then the first Cheeseburger has 0 upselling chances, but the second Cheeseburger has 2 upselling chances. Also, generally if a customer has a coupon for an item, but does not mention what item the coupon is for, then the coupon is generally meant for the next item in the order, unless the customer indicates that it is for one of the previous items ordered.
**Note**: If a customer orders a numbered item, meal, or combo with a specific size, the ordered burger comes with fries/side and a drink of the spcified size. If a size is not specified, then this is an opportunity for the call operator to upsize the item.
**Note**: If a certain item is out of stock (e.g. Large Drink Cups), That item should not be added to the list of ordered items. Because that item is not in the list of ordered items, there is not an opportunity to upsize that item. Instead, that item should be included in the missed selling opportunities area in the response guidelines. If the person decides to get a different item, include that new item in the order, but still note the original item in the missed selling opportunities area.
**Note**: The number of upsell/upsize offers can never be greater than the number of potential upsell/upsize opportunities. This is a hard rule that must be followed.
**Note**: If an operator offers a "meal" or a "combo" or "fries/side and/or drink", it counts as two offers per sandwhich, and applies to all sandwhiches the given order. If a customer already has an order for a sandwhich and side, and then an operator offers a "meal" or a "combo" or "side and/or drink", it counts as one offer per sandwhich and side, and applies to all such sandwhich and side the given order, and the items being offered for upselling are the sandwhiches and side. If a customer already has an order for a sandwhich and drink, and then an operator offers a "meal" or a "combo" or "side and/or drink", it counts as one offer per sandwhich and drink, and applies to all such sandwhich and drink the given order, and the items being offered for upselling are the sandwhiches and drinks. This is a hard rule that MUST be followed.
**Note**: If the customer selects a meal if the operator offers, then their conversion number is two per sandwhich that is made a meal. If the customer orders a sandwhich and side and then selects a meal if the operator offers, then their conversion number is one per sandwhich and side that is made a meal since 1 drink is added per meal added, and the items being converted are the sandwhich and side. If the customer orders a sandwhich and drink and then selects a meal if the operator offers, then their conversion number is one per sandwhich and drink that is made a meal since 1 side is added per meal added, and the items being converted are the sandwhich and drink. This still applies even if multiple of each item is ordered seperately. For example, if a customer order 5 sandwhiches, 2 sides and 4 drinks, then the customered ordered 2 meals and 2 sandwhich-drink pairs and 1 sandwhich, so the conversion number is 4 since 2 more sides would turn the 2 sandwhich-drink pairs into 2 meals and 1 side and 1 drink would turn the 1 sandwhich into a meal. Similarly, if a customer order 7 sandwhiches, 5 sides and 2 drinks, then the customered ordered 2 meals and 3 sandwhich-side pairs and 2 sandwhiches, so the conversion number is 7 since 3 more drinks would turn the 3 sandwhich-side pairs into 3 meals and 2 sides and 2 drinks would turn the 2 sandwhiches into 2 meals. This is a hard rule that must be followed.
**Note**: If the customer mentions a number in their order, unless they explicitly say it's a sandwhich only, it is a meal. This is a hard rule that must be followed.
**Note**: You must always reference the table for number of upsell/upsize opportunities. This is a hard rule that must be followed. Do not ever deviate from this.
**Note**: If the customer orders a meal and does not make it a large, there are two chances to upsize (a chance to upsize the side and a chance to upsize the drink). If a customer orders a sandwich, large fries, and a drink of unspecified size, then there is one chance to upsize (only a chance to upsize the drink), and the items being upsized are the sandwhich and large fries. If a customer orders a sandwich, large drink, and a fries of unspecified size, then there is one chance to upsize (only a chance to upsize the fries), and the items being upsized are the sandwhich and large drink.  This is a hard rule.
**Note**: Do not add things you cannot charge for (ketchup, mustard, etc.). Any item ordered must be included in the initial items ordered. This is a hard rule and must be followed.
**Note**: The number of items ordered after upsell, upsize, and additional topping chances must always equal the number of items ordered before upsell, upsize, and additional topping chances PLUS the number of successful upselling chances. This is a hard rule and must be followed.
**Note**: A valid add-on for any item is the addition of extra of that item itself. For example, if someone orders a cookie dough sundae, extra cookie dough is a valid add-on, and the operator should offer it to the customer. This is a hard rule and must be followed.
**Note**: If a customer has ordered an item that could be an upsell candidate, then only include the upsell chances for items not part of the initial order. For example, if a customer orders a chili dog and a drink, then the chance for upsell per json should only be for the fries. This is a hard rule and must be followed.
**Note**: If a customer has mentioned an item in their order that could be an upsell/upsize/add-on candidate, then do not count it as a candidate or opportunity for upsell/upsize/add-on. For example, if a customer initially orders a drink and then subs it out for a blizzard, don’t count the drink as an upsell opportunity.This is a hard rule that must be followed.
**Upsizing Scenarios**:
<<UPSIZING_JSON>>

**Note**: If the operator asks a customer what size they would like for an item, rather than specifically asking if they want the largest size of an item, that does not count as a valid upsizing offer.

**Initial Items Requested vs Items Ordered After Upselling and Upsizing Chances**
- **Scenario 1**: Customer orders a numbered item but not a meal initially, but upon being asked to upsell to a meal by an operator, agrees to get the numbered item meal. Initial item requested is the numbered item burger. Items ordered after upselling and upsizing is meal containing the numbered item burger, fries, and drink.
- **Scenario 2**: Customer orders a sandwich and orders a drink with no size specified, but upon being asked to upsize to a large drink by an operator, agrees. Initial item requested is a sandwich and drink. Items ordered after upselling and upsizing is sandwich and large drink.

**Additional Topping Scenarios**:
<<ADDONS_JSON>>

**Notes about Meals, Combos, and Numbered Items**:
- A customer may say that they want a specific burger or numbered item with fries and a drink without saying the word meal or the word combo, but they are getting the appropriate meal. For example, a Number 1 with large fries and a large drink is a Large Number 1 Meal.
- A burger can be tacitly upsized into a meal or combo when a side and a drink are also ordered.
- Similarly, a meal that does not have a specified size is upsized by making it a large size.
- If a meal has a specified size, then there is no opportunity to upsize.
- When a customer orders a meal, combo, or numbered item, it comes with 3 items: the burger, side, and a drink.
- The small, medium, or large meal/combo, and that just means that the sandwich is in a small, medium, or large size, and the side and drink are in the size specified in the meal table.
- Additionally, if a meal, combo, or numbered item is ordered, it cannot be upsold, but items in it can be upsized.
- A customer may order a meal or combo and then ask for a drink or side, but this drink or side comes with the meal/combo, so do not double count drinks or sides when appropriate.
- Make sure that upselling/upsizing offers and chances are per item, not per statement. So if 2 burgers are ordered in one statement by a customer, there are 2 offers to upsell per burger, for a total or 4 offers and 2 chances to upsell per burger, for a total or 4 chances.
- If a customer orders an item, but that item is upsold, then put the upsold item in the order, but for the purposes of upselling chance and upsizing chance, use the original item.
- If there is an item that is ordered in the transcript that does not match up with any items in the tables, it is likely mistranscribed: some of the words are missing (Chicken Bites vs. Rotisserie-Style Chicken Bites), spelled incorrectly (rice instead of fries), or some of the words are mixed up (Basket of Chicken Strips instead of Chicken Strips Basket). If this is the case for any items, use the context of the conversation and your own logic to figure out which menu item this is most likely referring to and write that down instead of the mistranscribed item.
- Assume that whenever a customer orders a Chicken Strip Basket of any kind, they are ordering the meal version (Chicken Strip Basket Meal) and not the item version, which does not exist in the table.

**Feedback Guidelines**:
- Use clear, structured feedback to evaluate the operator's handling of upselling and upsizing opportunities.
- Focus on adherence to best practices, valid phrasing, and alignment with the specific scenario.
- Highlight areas for improvement and commend any strengths or correct application of the suggestive selling process.

**Response Guidelines**:
You will be fed a several transcripts, with each transcript potentially with multiple transactions occurring in them. For each transaction, you will return the following in Python dictionary format. Format each entry and key of the dictionary as a single string. Do not add ```python to the front or ``` to the end. Wrap property names in double quotes. Make sure that the python dictionary ends with the right curly bracket, }. Make sure that there are no random line breaks. If there are multiple transactions in a single transcript, create one python dictionary for each transaction, with each dictionary seperated by the following 3 characters: @#& so that each transaction, even if they are from the same transcript, are in different rows in the spreadsheet and considered seperate from other transactions.. Generally, if there are multiple introductions like "Hello, welcome to Dairy Queen." in a transcript, there are multiple transactions in a transcript. Make the keys of the dictionary the number associated with the specific response guideline (e.g. 1 for the first entry, 2 for the second entry, etc.). For a transcript with multiple transactions, the transcript number for each transaction will be the same, but the transaction number will be different and the text of the transaction will be a section of the raw transcript.
Make sure that all integers are formatted as integers, not strings. This is a hard rule and must be followed.

CRITICAL FORMATTING RULE - ITEM ID USAGE:

**NEVER use item names. ALWAYS use the [Item ID]_[Size ID] format for ALL items.**

When indicating items, meals, add-ons, and any menu items, you MUST format them using ONLY the Item ID and Size ID numbers: [Item ID]_[Size ID]

**Examples:**
- Medium Misty Freeze (Item ID 16, Size ID 2) → Write as: 16_2
- Small Sundae (Item ID 1, Size ID 1) → Write as: 1_1  
- Pretzel Sticks (Item ID 4, Size ID 0) → Write as: 4_0
- Large Blizzard (Item ID 22, Size ID 3) → Write as: 22_3

**This applies to ALL item references including:**
- Initial items ordered (Field 1)
- Items that could be upsold (Field 4) 
- Items successfully upsold (Field 7)
- Items that could be upsized (Field 12)
- Items successfully upsized (Field 16)
- Additional toppings/add-ons (Field 19, 23)
- Final items after all changes (Field 25)
- ALL creator items (Fields 5, 8, 13, 17, 20, 24)

**NEVER write:**
- "Medium Misty Freeze"
- "Small Sundae" 
- "Pretzel Sticks"
- "Large Blizzard"
- Any descriptive item names

**ALWAYS write:**
- 16_2
- 1_1
- 4_0  
- 22_3
- Only the numeric Item ID and Size ID

**Size ID Reference:**
- 0 = No size/Default size
- 1 = Small/Kid's
- 2 = Medium/Regular  
- 3 = Large

**This is a HARD RULE that must be followed without exception. Any deviation from this format is incorrect.**

**For JSON/JSONB fields:** Use the same format within JSON arrays or objects:
- Correct: ["16_2", "1_1", "4_0"]
- Incorrect: ["Medium Misty Freeze", "Small Sundae", "Pretzel Sticks"]

**Reference the items.json file to find the correct Item ID and Size IDs for each menu item.**

1. Meals and items initially ordered by customer as a jsonb. Make sure this is a jsonb with no other text than the items ordered. Do not seperate the burgers, fries, and drinks into 3 seperate JSON entries. For example for meals, combos, and numbered items, if a Medium Number 1 Meal with Coke is Ordered, structure it as Medium Number 1 Meal (Number 1 Burger, Medium Fries, Medium Coke). If there are no items ordered, put a 0. Do not count items like condiments or ice water that do not add to the price of the order. Note: these are the items that the customer initially requests BEFORE the operator asks to upsell or upsize their items. The list items that are actually ordered AFTER the operator's upselling, upsizing, and additional toppings offers go into entry 19.
2. Number of Items Ordered. If a burger meal is ordered, it comes with 3 items: the burger, fries, and drink. Make sure that this is a number. Format this as an integer.

**Upsell**
3. Number of Chances to Upsell. If there are multiple of one item that can be upsold, count them all individually. For example, 2 Whoppers have 4 chances to upsell to a combo in total, not 2. Format this as an integer.
4. Items that are candidates for upselling as a jsonb. If there were no items, write the number 0. For example, if the customer ordered a burger only, the items that are candidates for upselling would be the fries and the drink.
Also output (non-numbered): 4_base — a jsonb array of the base items that created the upsell opportunities (e.g., the burgers that could be turned into meals). If none, write 0.
5. Number of Upselling Offers Made. Sometimes an operator may offer to upsell multiple items in the same offer. For example if a customer orders 2 Whoppers, the operator may ask if the customer wants to upsell both to meals. This would count as 2 offers, one for each Whopper. Format this as an integer.
6. Item candidates that were offered for upselling as a jsonb. If there were no candidates offered, write the number 0. For example, if the customer ordered a burger, the candidates that were offered for upselling would be the fries and the drink.
7. Items Successfully Upsold as a jsonb. If there were no items, write the number 0. Only put the items that were added to the order, not the items that were upsold (e.g. if a burger was upsold, put the fries and drink, not the burger).
8. Items that created the Successful Upselling Opportunities as a jsonb. These are the items that caused the upsell to happen. For example, if fries and a drink were upsold because a burger was ordered, then put the burger.
Also output (non-numbered): 8_base_sold — a jsonb array of the base items that were actually upsold (e.g., the burgers that were converted to meals). If none, write 0.
9. Number of Successful Upselling Offers. If an operator offers to upsell multiple items in the same offer, and a customer accepts, then count each item upsized separately. For example if an operator asks a customer if they want to upsize 2 Whoppers to 2 Whopper Meals and the customer accepts both, this would count as 4 successful chances, one for each Whopper upsized to a Whopper Meal. Format this as an integer.
10. Number of Items for which the Largest Option for that Item was Offered. If multiple of the largest size of the same item are ordered, like 3 offers to turn an order of fries into large fries, each order of large fries is counted separately, for a total of 3 times the largest option was offered. Format this as an integer.

**Upsize**
11. Number of Chances to Upsize. If there are multiple of one item that can be upsized, count them all individually. For example, 2 orders of fries have 2 chances to upsize to large fries, not 1.
Also output (non-numbered): 11_base — a jsonb array of the base items that created the upsize opportunities (e.g., small fries that could be upsized). If none, write 0.
12. Items in Order that Could be Upsized as a jsonb. If there were no items, write the number 0.
13. Items that created the Upsizing Opportunity as a jsonb. For example, if large fries were sold because fries of unspecified size were ordered, then put small fries. If a size is not specified, assume it is the smallest size. If there were no items, write the number 0.
14. Number of Upsizing Offers Made. Sometimes an operator may offer to upsize multiple items in the same offer. For example if a customer orders 2 fries, the operator may ask if the customer wants to upsize both to a large. This would count as 2 offers, one for each order of fries. Format this as an integer.
Also output (non-numbered): 14_base — a jsonb array of the base items that created the upsize opportunities (e.g., small fries that could be upsized). If none, write 0.
15. Number of Items Successfully Upsized. If an operator offers to upsize multiple items in the same offer, and a customer accepts, then count each item upsized separately. If 3 orders of fries were upsized, count each one separately, for a total count of 3. Format this as an integer.
16. Items Successfully Upsized as a jsonb. If there were no items, write the number 0.
Also output (non-numbered): 16_base_sold — a jsonb array of the base items that were actually upsized (e.g., the small fries that were converted to large fries). If none, write 0.

**Add-ons**
18. Number of Chances to add Additional Toppings. If there are multiple of one item that can have additional toppings, count them all individually. For example, 2 Blizzards = 2 chances. Format this as an integer.
Also output (non-numbered): 18_base — a jsonb array of the base items that created the add-on opportunities (e.g., sundae that can have extra toppings). If none, write 0.
19. Additional toppings that could have been added as a jsonb. If there were no items, write the number 0.
20. Items that created the Additional Topping Opportunities as a jsonb. For example, if whipped cream was offered because a sundae was ordered, then put the sundae. If none, write 0.
21. Number of Additional Toppings Offers Made. Format this as an integer.
Also output (non-numbered): 21_base — a jsonb array of the base items that created the add-on opportunities (e.g., sundae that can have extra toppings). If none, write 0.
22. Number of Successful Additional Toppings offers. Format this as an integer.
23. Items that additional toppings were added successfully. If there were no items, write the number 0.
Also output (non-numbered): 23_base_sold — a jsonb array of the base items that had additional toppings successfully added (e.g., the sundaes that got extra toppings). If none, write 0.

**After Order**
25. Meals and items ordered by customer AFTER upsells, upsizes, and additional toppings offers. Single jsonb, same rules as field 1. If no items, put 0.
26. Number of Items ordered by customer AFTER upsells, upsizes, and additional toppings offers. Format this as an integer.
27. Structured feedback, as a string with no line breaks. Do not use double quotes inside the feedback.
28. List where in the table you found your answer, and list any difficulties, ambiguities, or conflicting instructions encountered. You must list where you found your answer. This is a hard rule.

**JSON of Menu Items with Ordered Item Counts, Upselling Opportunities, and Upsizing Opportunities**:
- Below this line, a JSON file will be inserted containing all items on the Dairy Queen menu along with relevant information like the ordered item count, item inclusions, opportunities for upselling, and oportunities for upsizing.
- When creating the response, reference this JSON and double check that all entered information is correct according to this JSON file
<<ITEMS_JSON>>

**JSON of Menu Meals with Ordered Item Counts, Upselling Opportunities, and Upsizing Opportunities**:
- Below this line, a JSON file will be inserted containing all meals on the Dairy Queen menu along with relevant information like the ordered item count, item inclusions, opportunities for upselling, and oportunities for upsizing.
- When creating the response, whenever a customer requests a meal or asks to upsize an item to a meal, reference this JSON and double check that all entered information is correct according to this JSON file
<<MEALS_JSON>>
"""
    return (template
            .replace("<<UPSELLING_JSON>>", json.dumps(upselling))
            .replace("<<UPSIZING_JSON>>", json.dumps(upsizing))
            .replace("<<ADDONS_JSON>>", json.dumps(addons))
            .replace("<<ITEMS_JSON>>", json.dumps(items))
            .replace("<<MEALS_JSON>>", json.dumps(meals)))

# STEP2_PROMPT will be built dynamically with location-specific data
# This is now handled in grade_transactions() function

INITIAL_PROMPT = """
**Response Guidelines**:
You will be fed a single transcript with potentially multiple transactions occurring. Using your best judgement, split the transcript into multiple transactions. You will return a list of dictionaries, with one dictionary for each transaction. For each transaction, you will return the following in Python dictionary format. Format each entry and key of the dictionary as a single string. Do not add ```python to the front or ``` to the end. Wrap property names in double quotes. Make sure that the python dictionary ends with the right curly bracket, }. Make sure that there are no random line breaks. If there are multiple transactions in a single transcript, create one python dictionary for each transaction, with each dictionary seperated by the folling 3 characters: @#&. Generally, if there are multiple introductions like "Hello, welcome to Dairy Queen." in a transcript, there are multiple transactions in a transcript, but most often there is only 1 transaction in a transcript. Also, if a transcript is spoken in a language other than English, like Spanish, only use English when filling in the columns. Make the keys of the dictionary the number associated with the specific response guideline (e.g. 1 for the first entry, 2 for the second entry, etc.).
1. The full transcript, noting whether the operator or the customer is speaking each line. Seperate each line in the transcript with a new line. Make sure that this contains the entirety of the transcript and DO NOT SUMMARIZE THIS. This is a hard rule.
2. Analyze the transcript and based on the words and coherence of the sentences in the transcript, Return a 1 if this is likely to be a complete transcript and a 0 if this is likely to be a partial transcript with a significant number of words omitted or mis-transcribed. Partial Transcripts often have no items ordered or have the operator asking the customer to wait as the only sentence in the transcript. Also, if a significant amount of the transaction is in a language other than English, like Spanish, return a 0. In addition, a person wants to order an item, but is not able to due to that item being out of stock, and ultimately chooses not to order any items, return a 0. If the customer is picking up a mobile order and not ordering any other items, then the transcript is not complete.
3. Whether this is a mobile order. Write 1 if it is, and 0 of it is not.
4. Whether a coupon is used in the order. Write 1 if it is, and 0 of it is not.
5. Whether the operator asks the customer to wait for some time. Write 1 if it is, and 0 of it is not.
6. Items in Order that Could not be Sold Due to Being Out of Stock. If there were no items, write the number 0.
7. You must use the table and find exact references in the table for your answers. This is a hard rule and must be followed.
"""

# ---------- Utilities ----------
@contextlib.contextmanager
def _tmp_audio_from_video(video_path: str):
    # Create a permanent audio directory instead of temporary
    audio_dir = "extracted_audio"
    os.makedirs(audio_dir, exist_ok=True)
    
    # Generate audio filename based on video filename
    video_basename = os.path.splitext(os.path.basename(video_path))[0]
    out = os.path.join(audio_dir, f"{video_basename}_full_audio.mp3")
    
    clip = VideoFileClip(video_path)
    if clip.audio is None:
        clip.close()
        raise RuntimeError("No audio track in video")
    
    print(f"🎵 Extracting full audio to: {out}")
    clip.audio.write_audiofile(out, verbose=False, logger=None)
    duration = float(clip.duration or 0.0)
    clip.close()
    
    print(f"✅ Full audio saved: {out} (duration: {duration:.1f}s)")
    try:
        yield out, duration
    finally:
        # Don't delete the audio file - keep it saved
        print(f"💾 Audio file preserved: {out}")

def _segment_active_spans(y: np.ndarray, sr: int, window_s: float = 15.0) -> List[tuple[float,float]]:
    # Mirrors your simple "average==0 → silence" logic to carve spans.
    interval = int(sr * window_s)
    idx, removed, prev_active = 0, 0, 0
    begins, ends = [], []
    y_list = y.tolist()
    while idx + interval < len(y_list) and idx >= 0:
        chunk_avg = float(np.average(y_list[idx: idx + interval]))
        if chunk_avg == 0.0:
            if prev_active == 1:
                ends.append((idx + removed)/sr)
                prev_active = 0
            del y_list[idx: idx+interval]
            removed += interval
        else:
            if prev_active == 0:
                begins.append((idx + removed)/sr)
                prev_active = 1
            idx += interval
    if len(begins) != len(ends):
        ends.append((len(y_list)+removed)/sr)
    return list(zip(begins, ends))

def _parse_dt_file_timestamp(s3_key: str) -> str:
    """
    Parse DT_File timestamp from S3 key.
    Format: DT_File{YYYYMMDDHHMMSSFFF}
    Example: DT_File20250817170001000 -> 2025-08-17T17:00:01.000Z
    """
    import re
    import datetime
    
    # Extract filename from S3 key path
    filename = s3_key.split('/')[-1]
    
    # Match DT_File format: DT_File + 17 digits (YYYYMMDDHHMMSSFFF)
    match = re.match(r'DT_File(\d{17})', filename)
    if not match:
        # Fallback: return current time if format doesn't match
        return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")
    
    timestamp_str = match.group(1)
    
    # Parse: YYYYMMDDHHMMSSFFF
    year = int(timestamp_str[0:4])
    month = int(timestamp_str[4:6])
    day = int(timestamp_str[6:8])
    hour = int(timestamp_str[8:10])
    minute = int(timestamp_str[10:12])
    second = int(timestamp_str[12:14])
    millisecond = int(timestamp_str[14:17])
    
    # Create datetime object
    dt = datetime.datetime(year, month, day, hour, minute, second, 
                          millisecond * 1000, datetime.timezone.utc)
    
    return dt.isoformat().replace("+00:00","Z")

def _iso_from_start(base_iso: str, seconds_from_start: float) -> str:
    base = dateparse.isoparse(base_iso)
    return (base + timedelta(seconds=float(seconds_from_start))).isoformat().replace("+00:00","Z")

def _json_or_none(txt: str) -> Dict[str, Any] | None:
    try:
        return json.loads(txt.strip())
    except Exception:
        return None

# ---------- 1) TRANSCRIBE (extract spans, per‑span ASR) ----------
def transcribe_video(local_path: str) -> List[Dict]:
    segs: List[Dict] = []
    
    # Create audio directory for segments
    audio_dir = "extracted_audio"
    os.makedirs(audio_dir, exist_ok=True)
    video_basename = os.path.splitext(os.path.basename(local_path))[0]
    
    with _tmp_audio_from_video(local_path) as (audio_path, duration):
        y, sr = librosa.load(audio_path, sr=None)
        spans = _segment_active_spans(y, sr, 15.0) or [(0.0, duration)]
        
        print(f"🎬 Processing {len(spans)} audio segments for {video_basename}")
        
        for i, (b, e) in enumerate(spans):
            # Create permanent segment audio file instead of temporary
            segment_audio = os.path.join(audio_dir, f"{video_basename}_segment_{i+1:03d}_{int(b)}s-{int(e)}s.mp3")
            
            # Ensure end time doesn't exceed video duration
            end_time = min(int(e+1), duration)
            clip = VideoFileClip(local_path).subclip(int(b), end_time)
            
            print(f"🎵 Saving segment {i+1}/{len(spans)}: {segment_audio}")
            clip.audio.write_audiofile(segment_audio, verbose=False, logger=None)
            clip.close()

            with open(segment_audio, "rb") as af:
                try:
                    txt = client.audio.transcriptions.create(
                        model=_settings.ASR_MODEL,
                        file=af,
                        response_format="text",
                        temperature=0.001,
                        prompt="Label each line as Operator: or Customer: where possible."
                    )
                    text = str(txt)
                    print(f"✅ Segment {i+1} transcribed: {len(text)} characters")
                except Exception as ex:
                    print(f"❌ ASR error for segment {i+1}: {ex}")
                    text = ""
            
            # Don't delete the segment audio file - keep it saved
            print(f"💾 Segment audio preserved: {segment_audio}")

            segs.append({"start": float(b), "end": float(e), "text": text})
    
    print(f"🎉 Completed transcription: {len(segs)} segments saved")
    return segs


# ---------- 2) SPLIT (Step‑1 prompt per segment, preserve your @#& format) ----------
def split_into_transactions(transcript_segments: List[Dict], video_started_at_iso: str, s3_key: str = None) -> List[Dict]:
    # Anchor all transaction times strictly to the video's database start time
    # (ignore filename/S3 key to avoid cross-day drift)
    actual_video_start = video_started_at_iso
    print(f"Using database timestamp: {actual_video_start}")
    
    results: List[Dict] = []
    for seg in transcript_segments:
        raw = seg.get("text","") or ""
        if not raw.strip():
            continue
        resp = client.responses.create(
            model=_settings.STEP1_MODEL,
            input=[{
                "role":"user",
                "content":[
                    {"type":"input_text","text": INITIAL_PROMPT},
                    {"type":"input_text","text": "This is the transcript of the call:\n"+raw}
                ]
            }],
            store=False,
            text={"format":{"type":"text"}},
            reasoning={"effort":"high","summary":"detailed"},
        )
        text_out = resp.output[1].content[0].text if hasattr(resp, "output") else ""
        print(f"\n=== STEP 1 (Transaction Splitting) RAW OUTPUT ===")
        print(f"Input transcript: {raw[:200]}...")
        print(f"Raw LLM response: {text_out}")
        print("=" * 50)
        
        parts = [p for p in text_out.split("@#&") if str(p).strip()]
        if not parts:
            parts = [json.dumps({"1": raw, "2": "0"})]

        seg_dur = max(0.001, float(seg["end"]) - float(seg["start"]))
        slice_dur = seg_dur / len(parts)
        for i, p in enumerate(parts):
            d = _json_or_none(p) or {}
            s_rel = float(seg["start"]) + i*slice_dur
            e_rel = float(seg["start"]) + (i+1)*slice_dur
            results.append({
                "started_at": _iso_from_start(actual_video_start, s_rel),
                "ended_at":   _iso_from_start(actual_video_start, e_rel),
                "kind": "order",
                "meta": {
                    "text": d.get("1", raw),
                    "complete_order": int(str(d.get("2","0")) or "0"),
                    "mobile_order": int(str(d.get("3","0")) or "0"),
                    "coupon_used": int(str(d.get("4","0")) or "0"),
                    "asked_more_time": int(str(d.get("5","0")) or "0"),
                    "out_of_stock_items": d.get("6","0"),
                    "step1_raw": p,
                    # Additional timing metadata
                    "video_start_seconds": s_rel,
                    "video_end_seconds": e_rel,
                    "s3_key": s3_key or "",
                    "segment_index": i,
                    "total_segments_in_video": len(parts)
                }
            })
    return results

# ---------- 3) GRADE (Step‑2 prompt per transaction, return ALL columns) ----------
def _map_step2_to_grade_cols(step2_obj: Dict[str,Any], tx_meta: Dict[str,Any]) -> Dict[str,Any]:
    """Map numbered Step-2 keys (UPDATED) to `public.grades` columns with candidates + offered + converted."""
    # Defaults
    def _ii(x, default=0):
        try:
            return int(x)
        except:
            return default

    # Parse JSON/JSONB-like fields
    def _parse_json_field(value, default="0"):
        if value is None:
            return default
        if isinstance(value, (list, dict)):
            return value
        if isinstance(value, str):
            s = value.strip()
            if s in ("", "0"):
                return default
            try:
                if s[0] in "{[":
                    import json
                    return json.loads(s)
                return value  # already a plain string like "0" or a CSV that upstream expects
            except:
                return value
        return value

    print(f"Step2 object: {step2_obj}")
    print(f"Tx meta: {tx_meta}")

    out = {
        # Meta flags from tx, unchanged
        "complete_order":   _ii(tx_meta.get("complete_order", 0)),
        "mobile_order":     _ii(tx_meta.get("mobile_order", 0)),
        "coupon_used":      _ii(tx_meta.get("coupon_used", 0)),
        "asked_more_time":  _ii(tx_meta.get("asked_more_time", 0)),
        "out_of_stock_items": tx_meta.get("out_of_stock_items", "0"),

        # BEFORE items
        "items_initial":         step2_obj.get("1", "0"),
        "num_items_initial":     _ii(step2_obj.get("2", 0)),

        # ---- Upsell (candidates → offered → converted) ----
        "num_upsell_opportunities": _ii(step2_obj.get("3", 0)),
        "upsell_base_items":        _parse_json_field(step2_obj.get("4_base", "0")),
        "upsell_candidate_items":   _parse_json_field(step2_obj.get("4", "0")),
        "num_upsell_offers":        _ii(step2_obj.get("5", 0)),
        "upsell_offered_items":     _parse_json_field(step2_obj.get("6", "0")),
        "upsell_success_items":     _parse_json_field(step2_obj.get("7", "0")),
        "upsell_base_sold_items":   _parse_json_field(step2_obj.get("8_base_sold", "0")),
        "num_upsell_success":       _ii(step2_obj.get("9", 0)),
        "num_largest_offers":       _ii(step2_obj.get("10", 0)),

        # ---- Upsize (candidates → offered → converted) ----
        "num_upsize_opportunities": _ii(step2_obj.get("11", 0)),
        "upsize_base_items":        _parse_json_field(step2_obj.get("11_base", "0")),
        "upsize_candidate_items":   _parse_json_field(step2_obj.get("12", "0")),
        "num_upsize_offers":        _ii(step2_obj.get("14", 0)),
        "upsize_offered_items":     _parse_json_field(step2_obj.get("14_base", "0")),
        "upsize_success_items":     _parse_json_field(step2_obj.get("16", "0")),
        "upsize_base_sold_items":   _parse_json_field(step2_obj.get("16_base_sold", "0")),
        "num_upsize_success":       _ii(step2_obj.get("15", 0)),

        # ---- Add-on (candidates → offered → converted) ----
        "num_addon_opportunities":  _ii(step2_obj.get("18", 0)),
        "addon_base_items":         _parse_json_field(step2_obj.get("18_base", "0")),
        "addon_candidate_items":    _parse_json_field(step2_obj.get("19", "0")),
        "num_addon_offers":         _ii(step2_obj.get("21", 0)),
        "addon_offered_items":      _parse_json_field(step2_obj.get("21_base", "0")),
        "addon_success_items":      _parse_json_field(step2_obj.get("23", "0")),
        "addon_base_sold_items":    _parse_json_field(step2_obj.get("23_base_sold", "0")),
        "num_addon_success":        _ii(step2_obj.get("22", 0)),

        # AFTER items
        "items_after":              step2_obj.get("25", "0"),
        "num_items_after":          _ii(step2_obj.get("26", 0)),

        # Text feedback
        "feedback":                 step2_obj.get("27", ""),
        "issues":                   step2_obj.get("28", ""),

        # Optional extras
        "reasoning_summary":        step2_obj.get("reasoning_summary", "")
    }
    print(f"Out: {out}")
    return out

def grade_transactions(transactions: List[Dict], db=None, location_id: str = None, testing=True) -> List[Dict]:
    graded: List[Dict] = []
    for tx in transactions:
        transcript = (tx.get("meta") or {}).get("text","")
        tx_meta = tx.get("meta") or {}
        
        if not transcript.strip():
            # produce an empty row but keep columns
            base = _map_step2_to_grade_cols({}, tx_meta)
            graded.append({
                # 4 booleans + score (for backwards compatibility)
                "upsell_possible": False,
                "upsell_offered":  False,
                "upsize_possible": False,
                "upsize_offered":  False,
                "score": 0.0,
                "details": base,
                "transcript": "",     # Empty transcript
                "gpt_price": 0.0      # No cost for empty
            })
            continue

        # Run Step‑2 with location-specific menu data
        step2_prompt = _build_step2_prompt(db, location_id)
        prompt = step2_prompt + "\n\nProcess this transcript:\n" + transcript
        try:
            if testing: 
                resp = client.responses.create(
                    model=_settings.STEP2_MODEL,
                    include=["reasoning.encrypted_content"],
                    input=[{"role":"user","content":[{"type":"input_text","text": prompt}]}],
                    store=False,
                    text={"format":{"type":"text"}},
                    reasoning={"effort":"high","summary":"detailed"},
                )

            else: 
                resp = client.responses.create(
                    model=_settings.STEP2_MODEL,
                    input=[{"role":"user","content":[{"type":"input_text","text": prompt}]}],
                    store=False,
                    text={"format":{"type":"text"}},
                    reasoning={"effort":"high","summary":"detailed"},
                )

            raw = resp.output[1].content[0].text if hasattr(resp,"output") else "{}"
            print(f"\n=== STEP 2 (Grading) RAW OUTPUT ===")
            print(f"Input transcript: {transcript[:200]}...")
            print(f"Raw LLM response: {raw}")
            print("=" * 50)
            
            parsed = _json_or_none(raw) or {}
            print(f"Parsed JSON: {parsed}")
            
            # Calculate GPT price from API usage
            gpt_price = 0.0
            if hasattr(resp, 'usage'):
                # OpenAI o3 pricing: $2/1k input tokens, $8/1k output tokens
                input_cost = (resp.usage.input_tokens / 1000) * 2.0
                output_cost = (resp.usage.output_tokens / 1000) * 8.0
                gpt_price = input_cost + output_cost
                print(f"GPT Price: ${gpt_price:.6f} (input: {resp.usage.input_tokens} tokens, output: {resp.usage.output_tokens} tokens)")
            
            print("=" * 50)
        except Exception as ex:
            print("Step‑2 error:", ex)
            parsed = {}
            gpt_price = 0.0

        details = _map_step2_to_grade_cols(parsed, tx.get("meta") or {})
        print(f"Mapped details: {details}")
        print("=" * 50)

        # Helper function for safe integer conversion
        def _ii(x, default=0): 
            try: return int(x)
            except: return default

        # Derive simple booleans + score (kept for backward compatibility)
        upsell_possible = _ii(parsed.get("3", 0)) > 0
        upsell_offered  = _ii(parsed.get("6", 0)) > 0  # Field 6 is num_upsell_offers
        upsize_possible = _ii(parsed.get("11", 0)) > 0  # Field 11 is num_upsize_opportunities
        upsize_offered  = _ii(parsed.get("14", 0)) > 0  # Field 14 is num_upsize_offers

        # score: if present, else a light heuristic
        score = parsed.get("score", None)
        if score is None:
            try:
                total_ops = _ii(parsed.get("3",0)) + _ii(parsed.get("11",0))
                total_off = _ii(parsed.get("6",0)) + _ii(parsed.get("14",0))
                score = float(total_off) / float(total_ops) if total_ops > 0 else 0.0
            except Exception:
                score = 0.0

        graded.append({
            "upsell_possible": bool(upsell_possible),
            "upsell_offered":  bool(upsell_offered),
            "upsize_possible": bool(upsize_possible),
            "upsize_offered":  bool(upsize_offered),
            "score":           float(score),
            "details":         details,
            "transcript":      transcript,  # Add raw transcript
            "gpt_price":       gpt_price    # Add calculated price
        })
    return graded