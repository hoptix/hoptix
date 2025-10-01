#!/usr/bin/env python3
"""
Grade transactions directly from CSV export without re-downloading videos.

This script reads a CSV export of transactions (like 20250914_203452_transactions.csv)
and runs the AI grading pipeline directly on the existing transcript data.

Usage:
    python grade_from_csv.py path/to/transactions.csv [--run-id RUN_ID]
"""

import sys
import os
import csv
import json
import argparse
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Settings
from integrations.db_supabase import Supa
from worker.adapter import grade_transactions

# Import upsert_grades directly to avoid voice diarization dependencies
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def upsert_grades(db, tx_ids: List[str], grades: List[Dict]):
    """Upsert grades to database"""
    # Import the correct upsert function from pipeline
    from worker.pipeline import upsert_grades as pipeline_upsert_grades
    pipeline_upsert_grades(db, tx_ids, grades)

def parse_csv_row(row: Dict[str, str]) -> Dict[str, Any]:
    """Convert a CSV row into the transaction format expected by grade_transactions"""
    
    # Parse the meta field - it's JSON in this CSV format
    meta = {}
    try:
        import json
        meta_json = json.loads(row.get('meta', '{}'))
        meta = meta_json
    except (json.JSONDecodeError, TypeError):
        # Fallback to individual columns if meta is not JSON
        if row.get('meta.text'):
            meta['text'] = row['meta.text']
        if row.get('meta.complete_order'):
            meta['complete_order'] = int(row['meta.complete_order']) if row['meta.complete_order'] else 0
        if row.get('meta.mobile_order'):
            meta['mobile_order'] = int(row['meta.mobile_order']) if row['meta.mobile_order'] else 0
        if row.get('meta.coupon_used'):
            meta['coupon_used'] = int(row['meta.coupon_used']) if row['meta.coupon_used'] else 0
        if row.get('meta.asked_more_time'):
            meta['asked_more_time'] = int(row['meta.asked_more_time']) if row['meta.asked_more_time'] else 0
        if row.get('meta.out_of_stock_items'):
            meta['out_of_stock_items'] = row['meta.out_of_stock_items']
    
    # Create transaction object in expected format
    transaction = {
        'id': row.get('id', ''),  # Use the transaction ID directly
        'started_at': row.get('started_at', ''),
        'ended_at': row.get('ended_at', ''),
        'tx_range': row.get('tx_range', ''),
        'run_id': row.get('run_id', ''),
        'meta': meta
    }
    
    return transaction

def grade_from_csv(csv_path: str, run_id_filter: str = None) -> None:
    """Grade transactions from CSV export"""
    
    settings = Settings()
    db = Supa(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    
    print(f"🎯 Starting direct grading from CSV: {csv_path}")
    
    # Read CSV file
    transactions = []
    tx_ids = []
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Parse row into transaction format first
            transaction = parse_csv_row(row)
            
            # Skip empty transcript rows
            if not transaction.get('meta', {}).get('text', '').strip():
                continue
                
            # Filter by run_id if specified
            if run_id_filter and row.get('run_id') != run_id_filter:
                continue
            
            transactions.append(transaction)
            
            # Use the transaction ID directly from the CSV
            tx_ids.append(transaction['id'])
    
    print(f"📊 Found {len(transactions)} transactions with transcripts to grade")
    
    if not transactions:
        print("❌ No transactions found to grade")
        return
    
    # Run grading on all transactions
    print(f"🤖 Starting AI grading for {len(transactions)} transactions...")
    start_time = datetime.now()
    
    try:
        # For CSV grading, we'll use the first transaction's location_id if available
        location_id = None
        if transactions and 'location_id' in transactions[0]:
            location_id = transactions[0]['location_id']
            print(f"📍 Using location ID: {location_id}")
        else:
            print("⚠️ No location_id found in transactions, using JSON fallback")
        
        grades = grade_transactions(transactions, db, location_id)
        print(f"✅ Grading completed: {len(grades)} grades generated")
        
        # We already have the transaction IDs from the CSV, so we can use them directly
        print(f"💾 Upserting {len(grades)} grades to database...")
        upsert_grades(db, tx_ids, grades)
        print(f"✅ Grades successfully stored in database")
        
        duration = datetime.now() - start_time
        print(f"🎉 Processing completed!")
        print(f"   ⏱️ Total time: {duration.total_seconds():.1f} seconds")
        print(f"   📈 Results: {len(transactions)} transcripts → {len(grades)} grades stored")
        
    except Exception as e:
        duration = datetime.now() - start_time
        print(f"💥 Processing failed after {duration.total_seconds():.1f} seconds")
        print(f"   🚨 Error: {str(e)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Grade transactions from CSV export')
    parser.add_argument('csv_path', help='Path to the CSV export file')
    parser.add_argument('--run-id', help='Filter by specific run ID (optional)')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.csv_path):
        print(f"❌ CSV file not found: {args.csv_path}")
        sys.exit(1)
    
    grade_from_csv(args.csv_path, args.run_id)

if __name__ == "__main__":
    main()
