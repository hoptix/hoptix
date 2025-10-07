#!/usr/bin/env python3
"""
Generate comprehensive worker analytics report
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analytics import Analytics
import json
from services.database import Supa
db = Supa()

def get_all_workers():
    result = db.client.table("workers").select("*").execute()
    return result.data if result.data else []

def generate_worker_report():
    """Generate comprehensive worker analytics report for all workers"""
    
    # Run details
    run_ids = ["04756716-6564-4b2c-9396-4d72eab50af9"]
    
    # All workers data
    workers = get_all_workers()
    print("=" * 80)
    print("🏪 COMPREHENSIVE WORKER ANALYTICS REPORT")
    print("=" * 80)
    print(f"📅 Run IDs: {', '.join(run_ids)}")
    print(f"👥 Processing {len(workers)} workers across {len(run_ids)} runs...")
    print("=" * 80)
    print()
    
    # Process each run
    for run_idx, run_id in enumerate(run_ids, 1):
        print(f"🏃‍♂️ RUN {run_idx}/{len(run_ids)}: {run_id}")
        print("=" * 60)
        
        # Process each worker for this run
        for worker_idx, worker in enumerate(workers, 1):
            worker_id = worker["id"]
            worker_name = worker["legal_name"]
            worker_display = worker["display_name"]
            
            print(f"🔄 Processing Worker {worker_idx}/{len(workers)}: {worker_display}")
            print("-" * 40)
            
            try:
                # Create analytics instance for the worker
                analytics = Analytics(run_id=run_id, worker_id=worker_id)
                
                # Generate full analytics
                analytics_data = analytics.generate_analytics_json()
                
                # Display comprehensive report
                print("📊 PERFORMANCE SUMMARY")
                print("-" * 40)
                print(f"Total Transactions: {analytics_data['total_transactions']}")
                print(f"Complete Transactions: {analytics_data['complete_transactions']}")
                print(f"Completion Rate: {analytics_data['completion_rate']:.1%}")
                print(f"Avg Items Initial: {analytics_data['avg_items_initial']:.1f}")
                print(f"Avg Items Final: {analytics_data['avg_items_final']:.1f}")
                print(f"Avg Item Increase: {analytics_data['avg_item_increase']:.1f}")
                print()
                
                print("🔄 UPSELLING PERFORMANCE")
                print("-" * 40)
                print(f"Opportunities: {analytics_data['upsell_opportunities']}")
                print(f"Offers Made: {analytics_data['upsell_offers']}")
                print(f"Successes: {analytics_data['upsell_successes']}")
                print(f"Conversion Rate: {analytics_data['upsell_conversion_rate']:.1%}")
                print(f"Revenue: ${analytics_data['upsell_revenue']:.2f}")
                print()
                
                print("📏 UPSIZING PERFORMANCE")
                print("-" * 40)
                print(f"Opportunities: {analytics_data['upsize_opportunities']}")
                print(f"Offers Made: {analytics_data['upsize_offers']}")
                print(f"Successes: {analytics_data['upsize_successes']}")
                print(f"Conversion Rate: {analytics_data['upsize_conversion_rate']:.1%}")
                print(f"Revenue: ${analytics_data['upsize_revenue']:.2f}")
                print()
                
                print("➕ ADD-ON PERFORMANCE")
                print("-" * 40)
                print(f"Opportunities: {analytics_data['addon_opportunities']}")
                print(f"Offers Made: {analytics_data['addon_offers']}")
                print(f"Successes: {analytics_data['addon_successes']}")
                print(f"Conversion Rate: {analytics_data['addon_conversion_rate']:.1%}")
                print(f"Revenue: ${analytics_data['addon_revenue']:.2f}")
                print()
                
                print("🎯 OVERALL PERFORMANCE")
                print("-" * 40)
                print(f"Total Opportunities: {analytics_data['total_opportunities']}")
                print(f"Total Offers: {analytics_data['total_offers']}")
                print(f"Total Successes: {analytics_data['total_successes']}")
                print(f"Overall Conversion Rate: {analytics_data['overall_conversion_rate']:.1%}")
                print(f"Total Revenue: ${analytics_data['total_revenue']:.2f}")
                print()
                
                # Get detailed item analytics
                item_analytics = analytics.get_item_analytics()
                
                print("🍔 TOP PERFORMING ITEMS")
                print("-" * 40)
                
                # Find items with the most activity
                items_with_activity = []
                for item_id, item_data in item_analytics.items():
                    total_activity = 0
                    for size_data in item_data['sizes'].values():
                        total_activity += (size_data['upsell_base'] + size_data['upsize_base'] + size_data['addon_base'] +
                                         size_data['upsell_offered'] + size_data['upsize_offered'] + size_data['addon_offered'])
                    
                    if total_activity > 0:
                        items_with_activity.append((item_id, item_data['name'], total_activity))
                
                # Sort by activity
                items_with_activity.sort(key=lambda x: x[2], reverse=True)
                
                for i, (item_id, item_name, activity) in enumerate(items_with_activity[:10]):
                    print(f"{i+1:2d}. {item_name} (Activity: {activity})")
                print()
                
                # Show size transitions
                print("🔄 SIZE TRANSITIONS")
                print("-" * 40)
                items_with_transitions = []
                for item_id, item_data in item_analytics.items():
                    total_transitions = sum(item_data['transitions'].values())
                    if total_transitions > 0:
                        items_with_transitions.append((item_id, item_data['name'], item_data['transitions']))
                
                if items_with_transitions:
                    for item_id, item_name, transitions in items_with_transitions:
                        print(f"• {item_name}:")
                        for transition, count in transitions.items():
                            if count > 0:
                                size_names = {"1_to_2": "Small→Medium", "1_to_3": "Small→Large", "2_to_3": "Medium→Large"}
                                print(f"  - {size_names.get(transition, transition)}: {count}")
                else:
                    print("No size transitions recorded")
                print()
                
                # Try to upload to database
                print("💾 UPLOADING TO DATABASE")
                print("-" * 40)
                try:
                    result = analytics.upload_to_db()
                    print("✅ Successfully uploaded worker analytics to database!")
                    print(f"   Database result: {result}")
                except Exception as e:
                    print(f"❌ Error uploading to database: {e}")
                    print("   (This might be expected if the run_analytics_worker table doesn't exist yet)")
                print()
                
                # Save detailed JSON to file
                output_file = f"worker_analytics_report_{worker_id}_{run_id}.json"
                with open(output_file, 'w') as f:
                    json.dump(analytics_data, f, indent=2)
                print(f"💾 Detailed analytics saved to: {output_file}")
                print()
                
            except Exception as e:
                print(f"❌ Error generating report for {worker_display}: {e}")
                import traceback
                traceback.print_exc()
                print()
        
        print("=" * 80)
        print(f"📋 RUN {run_idx} COMPLETE")
        print("=" * 80)
        print()
    
    print("=" * 80)
    print("🎉 ALL REPORTS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    generate_worker_report()

