#!/usr/bin/env python3
"""
Test script to run worker analytics for all workers in all runs.
This script will:
1. Get all runs from the database
2. For each run, get all unique workers
3. Generate analytics for each worker in each run
4. Upload the analytics to the database
"""

import sys
import os
from datetime import datetime
import time

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from services.database import Supa
from services.analytics import Analytics

def get_all_runs():
    """Get all runs from the database"""
    db = Supa()
    result = db.client.table("runs").select("id, run_date, location_id").order("run_date", desc=True).execute()
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

def run_worker_analytics_for_run(run_id, workers):
    """Run analytics for all workers in a specific run"""
    print(f"\n🔄 Processing run {run_id} with {len(workers)} workers...")
    
    results = []
    for worker_id, employee_name in workers.items():
        print(f"  👤 Processing worker {worker_id} ({employee_name})...")
        
        try:
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
    """Main function to run worker analytics for all runs"""
    print("🚀 Starting Worker Analytics Generation")
    print("=" * 60)
    
    # Get all runs
    print("📊 Fetching all runs...")
    runs = get_all_runs()
    print(f"Found {len(runs)} runs")
    
    if not runs:
        print("❌ No runs found in database")
        return
    
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
        run_results = run_worker_analytics_for_run(run_id, workers)
        all_results.extend(run_results)
        
        # Update counters
        for result in run_results:
            total_workers_processed += 1
            if result["status"] == "success":
                successful_workers += 1
            else:
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
        else:
            print(f"❌ {result['run_id'][:8]}... | {result['worker_id'][:8]}... | "
                  f"{result['employee_name']} | ERROR: {result['error']}")
    
    # Save results to file
    results_file = f"worker_analytics_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    import json
    with open(results_file, 'w') as f:
        json.dump({
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
