#!/usr/bin/env python3
"""
Test script for analytics integration with graded_rows_filtered view
"""

import sys
sys.path.insert(0, '.')

from integrations.db_supabase import Supa
from config import Settings
from services.analytics_service import HoptixAnalyticsService
from dotenv import load_dotenv
import json

def main():
    """Test analytics integration with database"""
    
    load_dotenv()
    settings = Settings()
    db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    
    print("🔍 Testing Analytics Integration with Database")
    print("=" * 50)
    
    try:
        # Test query to graded_rows_filtered view
        print("📋 Querying graded_rows_filtered view...")
        result = db.client.from_('graded_rows_filtered').select('*').limit(10).execute()
        
        if not result.data:
            print("❌ No data found in graded_rows_filtered view")
            print("   Make sure the view exists and contains data")
            return
        
        print(f"✅ Found {len(result.data)} transactions (showing first 10)")
        
        # Show available columns
        if result.data:
            print(f"📊 Available columns: {list(result.data[0].keys())}")
            
            # Check for run_id column
            if 'run_id' in result.data[0]:
                run_ids = list(set(row.get('run_id') for row in result.data if row.get('run_id')))
                print(f"🔄 Available run_ids: {run_ids[:5]}")  # Show first 5
                
                if run_ids:
                    # Test analytics on first run_id
                    test_run_id = run_ids[0]
                    print(f"\n📊 Testing analytics for run_id: {test_run_id}")
                    
                    # Get all transactions for this run
                    run_result = db.client.from_('graded_rows_filtered').select('*').eq('run_id', test_run_id).execute()
                    print(f"📋 Found {len(run_result.data)} transactions for this run")
                    
                    if run_result.data:
                        # Run analytics
                        analytics_service = HoptixAnalyticsService()
                        report = analytics_service.generate_comprehensive_report(run_result.data)
                        
                        # Display summary
                        print("\n📊 ANALYTICS SUMMARY")
                        print("-" * 30)
                        summary = report['summary']
                        print(f"Total Transactions: {summary['total_transactions']}")
                        print(f"Complete Transactions: {summary['complete_transactions']}")
                        print(f"Completion Rate: {summary['completion_rate']:.1f}%")
                        
                        # Upselling
                        upselling = report['upselling']
                        print(f"🎯 Upselling: {upselling['total_successes']}/{upselling['total_opportunities']} ({upselling['conversion_rate']:.1f}%)")
                        
                        # Upsizing
                        upsizing = report['upsizing']
                        print(f"📏 Upsizing: {upsizing['total_successes']}/{upsizing['total_opportunities']} ({upsizing['conversion_rate']:.1f}%)")
                        
                        # Add-ons
                        addons = report['addons']
                        print(f"🍟 Add-ons: {addons['total_successes']}/{addons['total_opportunities']} ({addons['conversion_rate']:.1f}%)")
                        
                        print("\n✅ Analytics integration test successful!")
                        
                    else:
                        print("❌ No transactions found for this run_id")
            else:
                print("⚠️ run_id column not found in graded_rows_filtered view")
                print("   The view may need to be updated to include run_id")
        
    except Exception as e:
        print(f"❌ Error testing analytics integration: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())



