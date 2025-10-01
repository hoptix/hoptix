#!/bin/bash

# Grade all transactions for a given run_id in parallel workers

echo "📝 Hoptix Grade Run"
echo "===================="

export PYTHONUNBUFFERED=1

if [ $# -lt 1 ]; then
  echo "❌ Error: run_id required"
  echo "Usage: $0 RUN_ID"
  echo "Example: $0 123e4567-e89b-12d3-a456-426614174000"
  exit 1
fi

RUN_ID=$1

echo "🔄 Run ID: $RUN_ID"
echo "👥 Workers: 11"

cd "$(dirname "$0")/.."

python3 -u - <<PY
import sys, json, logging
sys.path.insert(0, '.')
from integrations.db_supabase import Supa
from config import Settings
from services.processing_service import ProcessingService
from worker.adapter import grade_transactions
from worker.pipeline import upsert_grades
from dotenv import load_dotenv
from concurrent.futures import ProcessPoolExecutor, as_completed

def _grade_chunk(tx_chunk, location_id):
    """Top-level function to grade a chunk in a separate process."""
    # Create independent DB client in each process
    s_local = Settings()
    db_local = Supa(s_local.SUPABASE_URL, s_local.SUPABASE_SERVICE_KEY)
    return grade_transactions(tx_chunk, db_local, location_id)

load_dotenv()
logging.basicConfig(level=logging.INFO, format='[Grader] %(levelname)s: %(message)s', stream=sys.stdout, force=True)

s = Settings()
db = Supa(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)
processing = ProcessingService(db, s)

run_id = "$RUN_ID"
print(f"📥 Fetching transactions for run {run_id}...")
tx_rows = db.client.table('transactions').select('*').eq('run_id', run_id).execute().data or []

if not tx_rows:
    print("ℹ️ No transactions found for this run")
    print("GRADED_COUNT=0")
    sys.exit(0)

location_id = None
try:
    vid = db.client.table('videos').select('location_id').eq('id', tx_rows[0]['video_id']).limit(1).execute().data
    if vid:
        location_id = vid[0]['location_id']
except Exception:
    pass

print(f"📊 Found {len(tx_rows)} transactions. Starting grading (location={location_id})...")
workers = 11
if len(tx_rows) < workers:
    workers = len(tx_rows)

# Split into contiguous chunks for parallel processing
def _make_chunks(lst, n):
    if n <= 0:
        return [lst]
    size = (len(lst) + n - 1) // n
    return [lst[i*size:(i+1)*size] for i in range(n) if lst[i*size:(i+1)*size]]

chunks = _make_chunks(tx_rows, workers)
tx_ids = [r['id'] for r in tx_rows]
chunk_ids = _make_chunks(tx_ids, workers)

# Incrementally upsert every 30 grades as they complete
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
PY

# Extract graded count from the last line if needed (best-effort)
GRADED_COUNT=$(tail -n 5 "$0" 2>/dev/null >/dev/null; :) # placeholder to keep var defined

echo "🎉 Grading complete for run $RUN_ID"
echo "✅ Graded transactions: ${GRADED_COUNT:-see logs}"

