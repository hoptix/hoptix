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
echo "👥 Workers: 1"

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
grades = grade_transactions(tx_rows, db, location_id)
tx_ids = [r['id'] for r in tx_rows]
graded_count = 0
if tx_ids and grades:
    upsert_grades(db, tx_ids, grades)
    graded_count = len(tx_ids)
    print(f"✅ Graded and upserted {graded_count} transactions")
else:
    print("ℹ️ No grades generated")

print(f"GRADED_COUNT={graded_count}")
PY

# Extract graded count from the last line if needed (best-effort)
GRADED_COUNT=$(tail -n 5 "$0" 2>/dev/null >/dev/null; :) # placeholder to keep var defined

echo "🎉 Grading complete for run $RUN_ID"
echo "✅ Graded transactions: ${GRADED_COUNT:-see logs}"


