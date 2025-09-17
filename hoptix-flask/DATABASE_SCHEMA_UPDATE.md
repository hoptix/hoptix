# Database Schema Update - Adding Missing Prompt Fields

## Overview
This update adds missing database columns to the `dev_grades` table to support all 28 prompt fields from the LLM grading system.

## Problem Solved
The original error `invalid literal for int() with base 10: '["42_0","42_0"]'` occurred because:
1. Field 5 from the LLM prompt contained a string array of items that created upselling opportunities
2. The system was trying to convert this to an integer because it was incorrectly mapped
3. Several "creator" fields from the prompt had no corresponding database columns

## New Database Columns Added

The following columns have been added to store items that created various opportunities:

| Column Name | Prompt Field | Type | Description |
|-------------|--------------|------|-------------|
| `items_upselling_creators` | Field 5 | jsonb | Items that created upselling opportunities |
| `items_upsold_creators` | Field 8 | jsonb | Items that created successful upselling opportunities |
| `items_upsizing_creators` | Field 13 | jsonb | Items that created upsizing opportunities |
| `items_upsize_creators` | Field 17 | jsonb | Items that created the actual upsizing |
| `items_addon_creators` | Field 20 | jsonb | Items that created additional topping opportunities |
| `items_addon_final_creators` | Field 24 | jsonb | Items that created the final additional toppings |

## How to Apply the Schema Changes

### Option 1: Using the SQL File (Recommended)
```bash
# Connect to your Supabase database and run:
psql -h your-supabase-host -U postgres -d postgres -f add_missing_columns.sql
```

### Option 2: Using Supabase Dashboard
1. Open your Supabase project dashboard
2. Go to the SQL Editor
3. Copy and paste the contents of `add_missing_columns.sql`
4. Click "Run"

### Option 3: Using psql directly
```sql
-- Run each ALTER TABLE command individually:
ALTER TABLE public.dev_grades ADD COLUMN IF NOT EXISTS items_upselling_creators jsonb NULL;
ALTER TABLE public.dev_grades ADD COLUMN IF NOT EXISTS items_upsold_creators jsonb NULL;
ALTER TABLE public.dev_grades ADD COLUMN IF NOT EXISTS items_upsizing_creators jsonb NULL;
ALTER TABLE public.dev_grades ADD COLUMN IF NOT EXISTS items_upsize_creators jsonb NULL;
ALTER TABLE public.dev_grades ADD COLUMN IF NOT EXISTS items_addon_creators jsonb NULL;
ALTER TABLE public.dev_grades ADD COLUMN IF NOT EXISTS items_addon_final_creators jsonb NULL;
```

## Code Changes Made

### 1. Updated Field Mapping (`worker/adapter.py`)
- Fixed incorrect mapping of prompt field 5 to `num_upsell_offers` (was causing integer conversion error)
- Added mapping for all creator fields to their new database columns
- Now all 28 prompt fields are properly mapped

### 2. Updated Database Upsert (`worker/pipeline.py`)
- Added the new creator columns to the database upsert operation
- Ensures all data from the LLM response is properly stored

## Complete Field Mapping Reference

| Prompt Field | Description | Database Column | Type |
|--------------|-------------|-----------------|------|
| 1 | Initial items ordered | `items_initial` | jsonb |
| 2 | Number of items ordered | `num_items_initial` | integer |
| 3 | Number of upsell chances | `num_upsell_opportunities` | integer |
| 4 | Items that could be upsold | `items_upsellable` | jsonb |
| 5 | Items that created upselling opportunities | `items_upselling_creators` | jsonb |
| 6 | Number of upselling offers made | `num_upsell_offers` | integer |
| 7 | Items successfully upsold | `items_upsold` | jsonb |
| 8 | Items that created successful upselling | `items_upsold_creators` | jsonb |
| 9 | Number of successful upselling offers | `num_upsell_success` | integer |
| 10 | Number of largest option offers | `num_largest_offers` | integer |
| 11 | Number of upsize chances | `num_upsize_opportunities` | integer |
| 12 | Items that could be upsized | `items_upsizeable` | jsonb |
| 13 | Items that created upsizing opportunities | `items_upsizing_creators` | jsonb |
| 14 | Number of upsizing offers made | `num_upsize_offers` | integer |
| 15 | Number of items successfully upsized | `num_upsize_success` | integer |
| 16 | Items successfully upsized | `items_upsize_success` | jsonb |
| 17 | Items that created the upsizing | `items_upsize_creators` | jsonb |
| 18 | Number of addon chances | `num_addon_opportunities` | integer |
| 19 | Additional toppings that could be added | `items_addonable` | jsonb |
| 20 | Items that created addon opportunities | `items_addon_creators` | jsonb |
| 21 | Number of addon offers made | `num_addon_offers` | integer |
| 22 | Number of successful addon offers | `num_addon_success` | integer |
| 23 | Items with successful addons | `items_addon_success` | jsonb |
| 24 | Items that created final addons | `items_addon_final_creators` | jsonb |
| 25 | Items after all changes | `items_after` | jsonb |
| 26 | Number of items after changes | `num_items_after` | integer |
| 27 | Structured feedback | `feedback` | text |
| 28 | Difficulties and ambiguities | `issues` | text |

## Testing
After applying the schema changes and deploying the code updates:
1. Process a video that previously failed with the integer conversion error
2. Verify that all prompt fields are properly stored in the database
3. Check that no data is lost during the mapping process

## Rollback (if needed)
If you need to rollback these changes:
```sql
ALTER TABLE public.dev_grades DROP COLUMN IF EXISTS items_upselling_creators;
ALTER TABLE public.dev_grades DROP COLUMN IF EXISTS items_upsold_creators;
ALTER TABLE public.dev_grades DROP COLUMN IF EXISTS items_upsizing_creators;
ALTER TABLE public.dev_grades DROP COLUMN IF EXISTS items_upsize_creators;
ALTER TABLE public.dev_grades DROP COLUMN IF EXISTS items_addon_creators;
ALTER TABLE public.dev_grades DROP COLUMN IF EXISTS items_addon_final_creators;
```
