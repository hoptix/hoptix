#!/usr/bin/env python3
"""
Test script for grade upload functionality.
Tests the complete flow from transaction creation to grade upload.
"""

import sys
import os
import json
import uuid
from datetime import datetime, timedelta

# Add the backend directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import Supa
from services.grader import grade_transactions
from services.transactions import split_into_transactions


def create_test_transactions():
    """Create test transaction data similar to the provided example."""
    
    # Mock transcript segments (similar to what transcribe_audio would return)
    transcript_segments = [
        {
            "start": 0.0,
            "end": 57.152,
            "text": "Customer: No, a small pumpkin pie blizzard and a medium pumpkin pie blizzard.\nCustomer: And those baskets come with fries, right?\nCustomer: Is that correct?\nOperator: Yes.\nOperator: Okay.\nOperator: Okay."
        },
        {
            "start": 57.152,
            "end": 114.304,
            "text": "Operator: Welcome to Dairy Queen. How may I help you?\nCustomer: Hi, can I get a brownie and Oreo cup section?\nOperator: Okay.\nCustomer: No, also a small vanilla milkshake.\nOperator: Okay.\nCustomer: And a small cheese blizzard.\nOperator: Okay.\nCustomer: And that's it. Thank you."
        }
    ]
    
    # Create a test run_id using proper UUID
    test_run_id = str(uuid.uuid4())
    test_date = "2025-10-08"
    
    print(f"🧪 Creating test transactions for run_id: {test_run_id}")
    
    # Split into transactions (this creates the transaction structure)
    transactions = split_into_transactions(transcript_segments, test_run_id, date=test_date)
    
    print(f"✅ Created {len(transactions)} test transactions")
    for i, tx in enumerate(transactions):
        print(f"   Transaction {i+1}: {tx.get('started_at')} - {tx.get('ended_at')}")
        print(f"   Text preview: {tx.get('meta', {}).get('text', '')[:100]}...")
    
    return transactions, test_run_id


def test_transaction_upload():
    """Test uploading transactions to database."""
    print("\n📤 Testing transaction upload...")
    
    db = Supa()
    transactions, test_run_id = create_test_transactions()
    
    try:
        # Upload transactions
        inserted_transactions = db.upsert_transactions(transactions)
        
        print(f"✅ Successfully uploaded {len(inserted_transactions)} transactions")
        
        # Verify transactions have IDs
        for i, tx in enumerate(inserted_transactions):
            if 'id' in tx:
                print(f"   Transaction {i+1} ID: {tx['id']}")
            else:
                print(f"   ❌ Transaction {i+1} missing ID!")
                return None
                
        return inserted_transactions
        
    except Exception as e:
        print(f"❌ Transaction upload failed: {e}")
        return None


def test_grade_creation_and_upload():
    """Test creating and uploading grades."""
    print("\n🎯 Testing grade creation and upload...")
    
    # First upload transactions
    inserted_transactions = test_transaction_upload()
    if not inserted_transactions:
        print("❌ Cannot test grades without transactions")
        return False
    
    # Test location ID (using the one from your example)
    test_location_id = "c3607cc3-0f0c-4725-9c42-eb2fdb5e016a"
    
    try:
        # Create grades
        print("🔍 Creating grades...")
        grades = grade_transactions(inserted_transactions, test_location_id, testing=True)
        
        print(f"✅ Created {len(grades)} grades")
        
        # Verify grade structure
        for i, grade in enumerate(grades):
            print(f"   Grade {i+1}:")
            print(f"     Transaction ID: {grade.get('transaction_id')}")
            print(f"     Has details: {'details' in grade}")
            print(f"     Has transcript: {'transcript' in grade}")
            print(f"     Has gpt_price: {'gpt_price' in grade}")
            
            if not grade.get('transaction_id'):
                print(f"     ❌ Grade {i+1} missing transaction_id!")
                return False
        
        # Upload grades
        print("📤 Uploading grades...")
        db = Supa()
        db.upsert_grades(grades)
        
        print("✅ Successfully uploaded grades!")
        return True
        
    except Exception as e:
        print(f"❌ Grade creation/upload failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_grade_structure():
    """Test the structure of created grades."""
    print("\n🔍 Testing grade structure...")
    
    # Create a simple test transaction with proper UUIDs
    test_transaction = {
        "id": str(uuid.uuid4()),
        "run_id": str(uuid.uuid4()),
        "started_at": "2025-10-08T07:00:00Z",
        "ended_at": "2025-10-08T07:00:57Z",
        "tx_range": '["2025-10-08T07:00:00Z","2025-10-08T07:00:57Z")',
        "kind": "order",
        "meta": {
            "text": "Customer: Can I get a small blizzard?\nOperator: Sure, what flavor?",
            "complete_order": 1,
            "mobile_order": 0,
            "coupon_used": 0,
            "asked_more_time": 0,
            "out_of_stock_items": "0"
        }
    }
    
    test_location_id = "c3607cc3-0f0c-4725-9c42-eb2fdb5e016a"
    
    try:
        # Test grade creation
        grades = grade_transactions([test_transaction], test_location_id, testing=True)
        
        if len(grades) != 1:
            print(f"❌ Expected 1 grade, got {len(grades)}")
            return False
            
        grade = grades[0]
        
        # Check required fields
        required_fields = ['transaction_id', 'details', 'transcript', 'gpt_price']
        for field in required_fields:
            if field not in grade:
                print(f"❌ Grade missing required field: {field}")
                return False
            else:
                print(f"   ✅ Has {field}: {type(grade[field])}")
        
        # Check details structure
        details = grade['details']
        expected_detail_fields = [
            'complete_order', 'mobile_order', 'coupon_used', 'asked_more_time',
            'out_of_stock_items', 'items_initial', 'num_items_initial'
        ]
        
        for field in expected_detail_fields:
            if field not in details:
                print(f"❌ Details missing field: {field}")
                return False
            else:
                print(f"   ✅ Details has {field}: {details[field]}")
        
        print("✅ Grade structure validation passed!")
        return True
        
    except Exception as e:
        print(f"❌ Grade structure test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def cleanup_test_data():
    """Clean up test data from database."""
    print("\n🧹 Cleaning up test data...")
    
    try:
        db = Supa()
        
        # Delete test transactions and grades
        # Note: This is a simple cleanup - in production you'd want more sophisticated cleanup
        print("   (Cleanup would go here - implement based on your needs)")
        print("✅ Cleanup completed")
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")


def main():
    """Run all grade upload tests."""
    print("🧪 Starting Grade Upload Tests")
    print("=" * 50)
    
    tests = [
        ("Grade Structure Test", test_grade_structure),
        ("Transaction Upload Test", test_transaction_upload),
        ("Grade Creation and Upload Test", test_grade_creation_and_upload),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🔬 Running: {test_name}")
        print("-" * 30)
        
        try:
            if test_name == "Transaction Upload Test":
                result = test_func() is not None
            else:
                result = test_func()
            results.append((test_name, result))
            
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
                
        except Exception as e:
            print(f"❌ {test_name} FAILED with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("💥 Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
