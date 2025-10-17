#!/usr/bin/env python3
"""
Test script for transaction upsert and delete functionality.
Tests upserting a transaction with run_id 53661c11-314e-447b-becc-81b606d81a37 and then deleting it.
"""

import sys
import os
from datetime import datetime

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database import Supa

def test_transaction_upsert_delete():
    """Test upserting and deleting a transaction with the specific run_id"""
    
    # Initialize database connection
    db = Supa()
    
    # Test run_id provided by user
    test_run_id = "53661c11-314e-447b-becc-81b606d81a37"
    
    print(f"🧪 Testing transaction upsert and delete for run_id: {test_run_id}")
    print("=" * 60)
    
    # Step 1: Create a test transaction
    test_transaction = {
        "run_id": test_run_id,
        "started_at": "2025-01-10T10:00:00Z",
        "ended_at": "2025-01-10T10:01:00Z",
        "tx_range": ["2025-01-10T10:00:00Z", "2025-01-10T10:01:00Z"],
        "kind": "order",
        "meta": {
            "text": "Test transaction for upsert/delete functionality",
            "complete_order": 1,
            "mobile_order": 0,
            "coupon_used": 0,
            "asked_more_time": 0,
            "out_of_stock_items": "0",
            "step1_raw": "Test data",
            "audio_start_seconds": 0.0,
            "audio_end_seconds": 60.0,
            "segment_index": 0,
            "total_segments_in_audio": 1
        }
    }
    
    print("📤 Step 1: Upserting test transaction...")
    try:
        # Upsert the transaction
        upserted_transactions = db.upsert_transactions([test_transaction])
        
        if upserted_transactions:
            print(f"✅ Successfully upserted transaction with ID: {upserted_transactions[0].get('id')}")
            test_transaction_id = upserted_transactions[0].get('id')
        else:
            print("❌ Failed to upsert transaction - no data returned")
            return False
            
    except Exception as e:
        print(f"❌ Error upserting transaction: {e}")
        return False
    
    # Step 2: Verify the transaction exists
    print("\n🔍 Step 2: Verifying transaction exists...")
    try:
        existing_transactions = db.get_transactions(test_run_id)
        
        if existing_transactions:
            print(f"✅ Found {len(existing_transactions)} transaction(s) for run_id {test_run_id}")
            for tx in existing_transactions:
                print(f"   - Transaction ID: {tx.get('id')}, Started: {tx.get('started_at')}")
        else:
            print(f"❌ No transactions found for run_id {test_run_id}")
            return False
            
    except Exception as e:
        print(f"❌ Error retrieving transactions: {e}")
        return False
    
    # Step 3: Delete the transaction
    print("\n🗑️  Step 3: Deleting transaction...")
    try:
        deleted_transactions = db.delete_transactions_by_run_id(test_run_id)
        print(f"✅ Successfully deleted transaction(s) for run_id {test_run_id}")
        
    except Exception as e:
        print(f"❌ Error deleting transaction: {e}")
        return False
    
    # Step 4: Verify the transaction is deleted
    print("\n🔍 Step 4: Verifying transaction is deleted...")
    try:
        remaining_transactions = db.get_transactions(test_run_id)
        
        if not remaining_transactions:
            print(f"✅ Confirmed: No transactions remain for run_id {test_run_id}")
        else:
            print(f"❌ Transaction still exists: {len(remaining_transactions)} transaction(s) found")
            return False
            
    except Exception as e:
        print(f"❌ Error verifying deletion: {e}")
        return False
    
    print("\n🎉 All tests passed! Transaction upsert and delete functionality is working correctly.")
    return True

if __name__ == "__main__":
    success = test_transaction_upsert_delete()
    sys.exit(0 if success else 1)
