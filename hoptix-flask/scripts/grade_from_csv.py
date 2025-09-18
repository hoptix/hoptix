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
from worker.pipeline import upsert_grades

def parse_csv_row(row: Dict[str, str]) -> Dict[str, Any]:
    """Convert a CSV row into the transaction format expected by grade_transactions"""
    
    # Parse the meta field - handling the CSV column structure
    meta = {}
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
        'id': row.get('video_id', ''),
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
            # Skip empty transcript rows
            if not row.get('meta.text', '').strip():
                continue
                
            # Filter by run_id if specified
            if run_id_filter and row.get('run_id') != run_id_filter:
                continue
            
            # Parse row into transaction format
            transaction = parse_csv_row(row)
            transactions.append(transaction)
            
            # Extract transaction ID - we'll need to look this up in the database
            # For now, we'll use video_id + tx_range as a unique identifier
            tx_id = f"{row.get('video_id', '')}_{row.get('tx_range', '')}"
            tx_ids.append(tx_id)
    
    print(f"📊 Found {len(transactions)} transactions with transcripts to grade")
    
    if not transactions:
        print("❌ No transactions found to grade")
        return
    
    # Run grading on all transactions
    print(f"🤖 Starting AI grading for {len(transactions)} transactions...")
    start_time = datetime.now()
    
    try:
        grades = grade_transactions(transactions)
        print(f"✅ Grading completed: {len(grades)} grades generated")
        
        # For CSV-based grading, we need to find the actual transaction IDs from the database
        print(f"🔍 Looking up transaction IDs in database...")
        
        actual_tx_ids = []
        for i, transaction in enumerate(transactions):
            video_id = transaction['id']
            started_at = transaction['started_at']
            ended_at = transaction['ended_at']
            
            try:
                # Query database for matching transaction
                result = db.client.table("transactions").select("id").eq("video_id", video_id).eq("started_at", started_at).eq("ended_at", ended_at).execute()
                
                if result.data:
                    actual_tx_ids.append(result.data[0]['id'])
                    print(f"✅ Found transaction ID for {video_id[:8]}... at {started_at[:19]}")
                else:
                    print(f"⚠️ Could not find transaction ID for video {video_id[:8]}... at {started_at[:19]}")
                    actual_tx_ids.append(None)
            except Exception as e:
                print(f"⚠️ Error looking up transaction ID: {e}")
                actual_tx_ids.append(None)
        
        # Filter out None values and pair with grades
        valid_pairs = [(tx_id, grade) for tx_id, grade in zip(actual_tx_ids, grades) if tx_id is not None]
        
        if valid_pairs:
            valid_tx_ids = [pair[0] for pair in valid_pairs]
            valid_grades = [pair[1] for pair in valid_pairs]
            
            print(f"💾 Upserting {len(valid_grades)} grades to database...")
            upsert_grades(db, valid_tx_ids, valid_grades)
            print(f"✅ Grades successfully stored in database")
        else:
            print("❌ No valid transaction IDs found - cannot store grades")
        
        duration = datetime.now() - start_time
        print(f"🎉 Processing completed!")
        print(f"   ⏱️ Total time: {duration.total_seconds():.1f} seconds")
        print(f"   📈 Results: {len(transactions)} transcripts → {len(valid_grades)} grades stored")
        
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
