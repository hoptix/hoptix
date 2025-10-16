#!/usr/bin/env python3
"""
Test script to grade a single transaction to verify the system works
before running the full batch grading.
"""

import sys
import json
import logging
import argparse
from dotenv import load_dotenv

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, '.')

from integrations.db_supabase import Supa
from config import Settings
from worker.adapter import grade_transactions
from worker.pipeline import upsert_grades


def test_single_transaction(run_id: str, location_id: str = None):
    """Test grading a single transaction from a run"""
    
    # Load environment variables
    load_dotenv()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, 
        format='[Test] %(levelname)s: %(message)s', 
        stream=sys.stdout, 
        force=True
    )

    print("🧪 Hoptix Single Transaction Test")
    print("==================================")
    print(f"🔄 Run ID: {run_id}")
    print(f"📍 Location ID: {location_id or 'Auto-detect'}")

    # Initialize services
    s = Settings()
    db = Supa(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)

    # Fetch one transaction from the run
    print(f"📥 Fetching one transaction from run {run_id}...")
    tx_result = db.client.table('transactions').select('*').eq('run_id', run_id).limit(50).execute()
    
    if not tx_result.data:
        print("❌ No transactions found for this run")
        return False
    
    tx = tx_result.data[45]
    print(f"✅ Found transaction: {tx['id']}")
    
    # Get location_id from video if not provided
    if not location_id:
        try:
            vid = db.client.table('videos').select('location_id').eq('id', tx['video_id']).limit(1).execute().data
            if vid:
                location_id = vid[0]['location_id']
                print(f"📍 Auto-detected location: {location_id}")
        except Exception as e:
            print(f"⚠️  Could not auto-detect location: {e}")
            location_id = None

    # Test the grading function
    print(f"🎯 Testing grade_transactions function...")
    try:
        # Convert transaction to the format expected by grade_transactions
        tx_for_grading = {
            'id': tx['id'],
            'meta': tx['meta'] or {}
        }
        
        # Grade the single transaction
        graded = grade_transactions([tx_for_grading], db, location_id, testing=True)
        
        if not graded:
            print("❌ No grades returned from grade_transactions")
            return False
            
        grade = graded[0]
        print(f"✅ Successfully graded transaction")
        print(f"   - Transcript length: {len(grade.get('transcript', ''))}")
        print(f"   - GPT Price: ${grade.get('gpt_price', 0):.6f}")
        print(f"   - Details keys: {list(grade.get('details', {}).keys())}")
        
        # Test the upsert function
        print(f"💾 Testing upsert_grades function...")
        try:
            upsert_grades(db, [tx['id']], graded)
            print("✅ Successfully upserted grade to database")
            
            # Verify the grade was actually saved
            verify_result = db.client.table('grades').select('*').eq('transaction_id', tx['id']).execute()
            if verify_result.data:
                saved_grade = verify_result.data[0]
                print(f"✅ Verified grade saved to database")
                print(f"   - Transaction ID: {saved_grade['transaction_id']}")
                print(f"   - Items initial: {saved_grade.get('items_initial', 'N/A')}")
                print(f"   - Items after: {saved_grade.get('items_after', 'N/A')}")
                print(f"   - Upsell opportunities: {saved_grade.get('num_upsell_opportunities', 0)}")
                print(f"   - Upsize opportunities: {saved_grade.get('num_upsize_opportunities', 0)}")
                print(f"   - Addon opportunities: {saved_grade.get('num_addon_opportunities', 0)}")
                return True
            else:
                print("❌ Grade not found in database after upsert")
                return False
                
        except Exception as e:
            print(f"❌ Error upserting grade: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Error grading transaction: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Test grading a single transaction')
    parser.add_argument('run_id', help='The run ID to test with')
    parser.add_argument('--location-id', help='Location ID (auto-detected if not provided)')
    args = parser.parse_args()

    try:
        success = test_single_transaction(args.run_id, args.location_id)
        if success:
            print("\n🎉 Test completed successfully!")
            print("✅ The grading system is working correctly")
            print("🚀 You can now run the full batch grading")
            sys.exit(0)
        else:
            print("\n❌ Test failed!")
            print("🔧 Please fix the issues before running full batch grading")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
