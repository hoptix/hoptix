-- run_analytics_with_details view
-- This view joins run_analytics with run metadata and location/org information

CREATE OR REPLACE VIEW public.run_analytics_with_details AS
SELECT 
    ra.*,
    r.run_date as run_date,
    r.location_id,
    r.org_id,
    l.name as location_name,
    o.name as org_name
FROM public.run_analytics ra
JOIN public.runs r ON ra.run_id = r.id
LEFT JOIN public.locations l ON r.location_id = l.id
LEFT JOIN public.orgs o ON r.org_id = o.id;

-- Add indexes on the underlying tables for view performance (if they don't exist)
CREATE INDEX IF NOT EXISTS idx_runs_location_id ON public.runs(location_id);
CREATE INDEX IF NOT EXISTS idx_runs_org_id ON public.runs(org_id);
CREATE INDEX IF NOT EXISTS idx_runs_run_date ON public.runs(run_date);
CREATE INDEX IF NOT EXISTS idx_locations_org_id ON public.locations(org_id);

COMMENT ON VIEW public.run_analytics_with_details IS 'Combines run_analytics with run metadata, location, and organization information for easier querying and API responses';