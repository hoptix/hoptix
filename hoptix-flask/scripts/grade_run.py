#!/usr/bin/env python3
"""
Grade all transactions for a given run_id in parallel workers
"""

import sys
import json
import logging
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dotenv import load_dotenv

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, '.')

from integrations.db_supabase import Supa
from config import Settings
from services.processing_service import ProcessingService
from worker.adapter import grade_transactions
from worker.pipeline import upsert_grades


def _grade_chunk(tx_chunk, location_id):
    """Top-level function to grade a chunk in a separate process."""
    # Create independent DB client in each process
    s_local = Settings()
    db_local = Supa(s_local.SUPABASE_URL, s_local.SUPABASE_SERVICE_KEY)
    return grade_transactions(tx_chunk, db_local, location_id)


def _make_chunks(lst, n):
    """Split list into n chunks"""
    if n <= 0:
        return [lst]
    size = (len(lst) + n - 1) // n
    return [lst[i*size:(i+1)*size] for i in range(n) if lst[i*size:(i+1)*size]]


def main():
    parser = argparse.ArgumentParser(description='Grade all transactions for a given run_id')
    parser.add_argument('run_id', help='The run ID to grade transactions for')
    parser.add_argument('--workers', type=int, default=11, help='Number of worker processes (default: 11)')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO, 
        format='[Grader] %(levelname)s: %(message)s', 
        stream=sys.stdout, 
        force=True
    )

    print("📝 Hoptix Grade Run")
    print("====================")
    print(f"🔄 Run ID: {args.run_id}")
    print(f"👥 Workers: {args.workers}")

    # Initialize services
    s = Settings()
    db = Supa(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)
    processing = ProcessingService(db, s)

    # Fetch transactions
    print(f"📥 Fetching transactions for run {args.run_id}...")
    tx_rows = db.client.table('transactions').select('*').eq('run_id', args.run_id).execute().data or []

    if not tx_rows:
        print("ℹ️ No transactions found for this run")
        print("GRADED_COUNT=0")
        return 0

    # Get location_id from first transaction's video
    location_id = None
    try:
        vid = db.client.table('videos').select('location_id').eq('id', tx_rows[0]['video_id']).limit(1).execute().data
        if vid:
            location_id = vid[0]['location_id']
    except Exception:
        pass

    print(f"📊 Found {len(tx_rows)} transactions. Starting grading (location={location_id})...")
    
    # Determine number of workers
    workers = args.workers
    if len(tx_rows) < workers:
        workers = len(tx_rows)

    # Split into chunks for parallel processing
    chunks = _make_chunks(tx_rows, workers)
    tx_ids = [r['id'] for r in tx_rows]
    chunk_ids = _make_chunks(tx_ids, workers)

    # Process chunks in parallel
    graded_count = 0
    buffer_grades = []
    buffer_ids = []

    if chunks:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            future_to_ids = {}
            for ch, ch_ids in zip(chunks, chunk_ids):
                fut = executor.submit(_grade_chunk, ch, location_id)
                future_to_ids[fut] = ch_ids

            for fut in as_completed(list(future_to_ids.keys())):
                res = fut.result() or []
                ch_ids = future_to_ids[fut]
                for g, tx_id in zip(res, ch_ids):
                    buffer_grades.append(g)
                    buffer_ids.append(tx_id)
                    if len(buffer_grades) >= 30:
                        upsert_grades(db, buffer_ids, buffer_grades)
                        graded_count += len(buffer_grades)
                        print(f"🚀 Upserted batch of {len(buffer_grades)} (total {graded_count})")
                        buffer_grades.clear()
                        buffer_ids.clear()

    # Flush any remaining grades
    if buffer_grades and buffer_ids:
        upsert_grades(db, buffer_ids, buffer_grades)
        graded_count += len(buffer_grades)
        print(f"🚀 Upserted final batch of {len(buffer_grades)} (total {graded_count})")

    if graded_count > 0:
        print(f"✅ Graded and upserted {graded_count} transactions")
    else:
        print("ℹ️ No grades generated")

    print(f"GRADED_COUNT={graded_count}")
    return graded_count


if __name__ == "__main__":
    try:
        graded_count = main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n⚠️ Grading interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during grading: {e}")
        logging.exception("Grading failed")
        sys.exit(1)
