-- SQL queries to add num_base_offered columns to grades table
-- Run these queries in your database to add the new columns

-- Add num_upsell_base_offered column
ALTER TABLE grades 
ADD COLUMN num_upsell_base_offered INTEGER DEFAULT 0;

-- Add num_upsize_base_offered column  
ALTER TABLE grades 
ADD COLUMN num_upsize_base_offered INTEGER DEFAULT 0;

-- Add num_addon_base_offered column
ALTER TABLE grades 
ADD COLUMN num_addon_base_offered INTEGER DEFAULT 0;

-- Optional: Add comments to document the columns
COMMENT ON COLUMN grades.num_upsell_base_offered IS 'Number of times base items were offered to be upsold';
COMMENT ON COLUMN grades.num_upsize_base_offered IS 'Number of times base items were offered to be upsized';
COMMENT ON COLUMN grades.num_addon_base_offered IS 'Number of times base items were offered to have additional toppings added';

-- Verify the columns were added
SELECT column_name, data_type, column_default 
FROM information_schema.columns 
WHERE table_name = 'grades' 
AND column_name IN ('num_upsell_base_offered', 'num_upsize_base_offered', 'num_addon_base_offered')
ORDER BY column_name;
