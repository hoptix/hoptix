-- Script to create sample workers for testing
-- This will insert sample workers if you don't have any yet

-- First check if we have workers
DO $$
DECLARE
    worker_count INTEGER;
    org_record RECORD;
BEGIN
    SELECT COUNT(*) INTO worker_count FROM public.workers;
    
    IF worker_count = 0 THEN
        RAISE NOTICE 'No workers found. Creating sample workers...';
        
        -- Create sample workers for each organization
        FOR org_record IN SELECT id, name FROM public.orgs LOOP
            INSERT INTO public.workers (org_id, legal_name, display_name, active) VALUES
            (org_record.id, 'John Smith', 'John S.', true),
            (org_record.id, 'Sarah Johnson', 'Sarah J.', true),
            (org_record.id, 'Michael Brown', 'Mike B.', true),
            (org_record.id, 'Emily Davis', 'Emily D.', true),
            (org_record.id, 'David Wilson', 'Dave W.', true),
            (org_record.id, 'Lisa Anderson', 'Lisa A.', true),
            (org_record.id, 'Robert Taylor', 'Rob T.', true),
            (org_record.id, 'Jennifer Martinez', 'Jen M.', true),
            (org_record.id, 'Christopher Lee', 'Chris L.', false), -- inactive worker
            (org_record.id, 'Amanda White', 'Amanda W.', true);
            
            RAISE NOTICE 'Created 10 workers for organization: %', org_record.name;
        END LOOP;
    ELSE
        RAISE NOTICE 'Found % existing workers. Skipping worker creation.', worker_count;
    END IF;
END $$;

-- Show summary of workers by organization
SELECT 
    o.name as organization,
    COUNT(w.id) as total_workers,
    COUNT(CASE WHEN w.active = true THEN 1 END) as active_workers,
    COUNT(CASE WHEN w.active = false THEN 1 END) as inactive_workers
FROM public.orgs o
LEFT JOIN public.workers w ON o.id = w.org_id
GROUP BY o.id, o.name
ORDER BY o.name;

-- Show all workers
SELECT 
    w.id,
    o.name as organization,
    w.legal_name,
    w.display_name,
    w.active
FROM public.workers w
JOIN public.orgs o ON w.org_id = o.id
ORDER BY o.name, w.legal_name;
