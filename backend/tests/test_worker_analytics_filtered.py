#!/usr/bin/env python3
"""
Filtered test script to run worker analytics for specific runs or date ranges.
Usage examples:
- python test_worker_analytics_filtered.py --run-id <run_id>
- python test_worker_analytics_filtered.py --date-range 2025-01-01 2025-01-31
- python test_worker_analytics_filtered.py --location-id <location_id>
- python test_worker_analytics_filtered.py --limit 5
"""

import sys
import os
import argparse
from datetime import datetime, timedelta
import time

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from services.database import Supa
from services.analytics import Analytics

def get_runs_filtered(run_id=None, start_date=None, end_date=None, location_id=None, limit=None):
    """Get filtered runs from the database"""
    db = Supa()
    query = db.client.table("runs").select("id, run_date, location_id")
    
    if run_id:
        query = query.eq("id", run_id)
    if start_date:
        query = query.gte("run_date", start_date)
    if end_date:
        query = query.lte("run_date", end_date)
    if location_id:
        query = query.eq("location_id", location_id)
    
    query = query.order("run_date", desc=True)
    
    if limit:
        query = query.limit(limit)
    
    result = query.execute()
    return result.data if result.data else []

def get_workers_for_run(run_id):
    """Get all unique workers for a specific run"""
    db = Supa()
    result = db.client.table("graded_rows_filtered").select("worker_id, employee_name").eq("run_id", run_id).execute()
    
    # Get unique workers
    workers = {}
    if result.data:
        for row in result.data:
            worker_id = row.get("worker_id")
            employee_name = row.get("employee_name", "Unknown")
            if worker_id:
                workers[worker_id] = employee_name
    
    return workers

def run_worker_analytics_for_run(run_id, workers, dry_run=False):
    """Run analytics for all workers in a specific run"""
    print(f"\n🔄 Processing run {run_id} with {len(workers)} workers...")
    
    results = []
    for worker_id, employee_name in workers.items():
        print(f"  👤 Processing worker {worker_id} ({employee_name})...")
        
        try:
            if dry_run:
                # Just simulate the process
                print(f"    🔍 DRY RUN: Would process analytics for worker {worker_id}")
                results.append({
                    "run_id": run_id,
                    "worker_id": worker_id,
                    "employee_name": employee_name,
                    "status": "dry_run",
                    "message": "Simulated processing"
                })
                continue
            
            # Create analytics instance for this worker and run
            analytics = Analytics(run_id=run_id, worker_id=worker_id)
            
            # Generate analytics
            start_time = time.time()
            analytics_data = analytics.generate_analytics_json()
            generation_time = time.time() - start_time
            
            # Upload to database
            upload_start = time.time()
            db_result = analytics.upload_to_db()
            upload_time = time.time() - start_time
            
            results.append({
                "run_id": run_id,
                "worker_id": worker_id,
                "employee_name": employee_name,
                "status": "success",
                "generation_time": round(generation_time, 2),
                "upload_time": round(upload_time, 2),
                "total_transactions": analytics_data.get("total_transactions", 0),
                "total_revenue": analytics_data.get("total_revenue", 0),
                "overall_conversion_rate": analytics_data.get("overall_conversion_rate", 0)
            })
            
            print(f"    ✅ Success: {analytics_data.get('total_transactions', 0)} transactions, "
                  f"${analytics_data.get('total_revenue', 0):.2f} revenue, "
                  f"{analytics_data.get('overall_conversion_rate', 0)*100:.1f}% conversion rate")
            
        except Exception as e:
            print(f"    ❌ Error: {str(e)}")
            results.append({
                "run_id": run_id,
                "worker_id": worker_id,
                "employee_name": employee_name,
                "status": "error",
                "error": str(e)
            })
    
    return results

def main():
    """Main function with command line arguments"""
    parser = argparse.ArgumentParser(description="Run worker analytics for filtered runs")
    parser.add_argument("--run-id", help="Specific run ID to process")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("--location-id", help="Specific location ID")
    parser.add_argument("--limit", type=int, help="Limit number of runs to process")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without actually processing")
    
    args = parser.parse_args()
    
    print("🚀 Starting Filtered Worker Analytics Generation")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual processing will occur")
    
    # Get filtered runs
    print("📊 Fetching filtered runs...")
    runs = get_runs_filtered(
        run_id=args.run_id,
        start_date=args.start_date,
        end_date=args.end_date,
        location_id=args.location_id,
        limit=args.limit
    )
    
    print(f"Found {len(runs)} runs matching criteria")
    
    if not runs:
        print("❌ No runs found matching the specified criteria")
        return
    
    # Show run details
    print("\n📋 Runs to process:")
    for i, run in enumerate(runs, 1):
        print(f"  {i}. {run['id']} - {run['run_date']} - Location: {run['location_id']}")
    
    # Process each run
    all_results = []
    total_workers_processed = 0
    successful_workers = 0
    failed_workers = 0
    
    start_time = time.time()
    
    for i, run in enumerate(runs, 1):
        run_id = run["id"]
        run_date = run["run_date"]
        location_id = run["location_id"]
        
        print(f"\n📅 Run {i}/{len(runs)}: {run_id}")
        print(f"   Date: {run_date}")
        print(f"   Location: {location_id}")
        
        # Get workers for this run
        workers = get_workers_for_run(run_id)
        
        if not workers:
            print(f"   ⚠️  No workers found for this run")
            continue
        
        # Run analytics for all workers in this run
        run_results = run_worker_analytics_for_run(run_id, workers, dry_run=args.dry_run)
        all_results.extend(run_results)
        
        # Update counters
        for result in run_results:
            total_workers_processed += 1
            if result["status"] == "success":
                successful_workers += 1
            elif result["status"] == "error":
                failed_workers += 1
    
    total_time = time.time() - start_time
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total runs processed: {len(runs)}")
    print(f"Total workers processed: {total_workers_processed}")
    print(f"Successful workers: {successful_workers}")
    print(f"Failed workers: {failed_workers}")
    if args.dry_run:
        print(f"Dry run simulations: {total_workers_processed - successful_workers - failed_workers}")
    print(f"Total time: {total_time:.2f} seconds")
    print(f"Average time per worker: {total_time/max(total_workers_processed, 1):.2f} seconds")
    
    # Print detailed results
    print("\n📋 DETAILED RESULTS")
    print("=" * 60)
    
    for result in all_results:
        if result["status"] == "success":
            print(f"✅ {result['run_id'][:8]}... | {result['worker_id'][:8]}... | "
                  f"{result['employee_name']} | {result['total_transactions']} txns | "
                  f"${result['total_revenue']:.2f} | {result['overall_conversion_rate']*100:.1f}%")
        elif result["status"] == "dry_run":
            print(f"🔍 {result['run_id'][:8]}... | {result['worker_id'][:8]}... | "
                  f"{result['employee_name']} | DRY RUN")
        else:
            print(f"❌ {result['run_id'][:8]}... | {result['worker_id'][:8]}... | "
                  f"{result['employee_name']} | ERROR: {result['error']}")
    
    # Save results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"worker_analytics_filtered_results_{timestamp}.json"
    import json
    with open(results_file, 'w') as f:
        json.dump({
            "filters": {
                "run_id": args.run_id,
                "start_date": args.start_date,
                "end_date": args.end_date,
                "location_id": args.location_id,
                "limit": args.limit,
                "dry_run": args.dry_run
            },
            "summary": {
                "total_runs": len(runs),
                "total_workers_processed": total_workers_processed,
                "successful_workers": successful_workers,
                "failed_workers": failed_workers,
                "total_time_seconds": total_time,
                "average_time_per_worker": total_time/max(total_workers_processed, 1)
            },
            "results": all_results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    print("🎉 Worker analytics generation completed!")

if __name__ == "__main__":
    main()
