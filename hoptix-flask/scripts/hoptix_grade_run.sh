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
NUM_WORKERS=11

echo "🔄 Run ID: $RUN_ID"
echo "👥 Workers: $NUM_WORKERS"

cd "$(dirname "$0")/.."

# Fetch all transaction IDs and shard them
SHARDS=$(python3 -u - <<PY
import sys, json
sys.path.insert(0, '.')
from integrations.db_supabase import Supa
from config import Settings
from dotenv import load_dotenv

load_dotenv()
s = Settings()
db = Supa(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)

run_id = "$RUN_ID"
num_workers = $NUM_WORKERS

print(f"📥 Fetching transactions for run {run_id}...", file=sys.stderr)
rows = db.client.table('transactions').select('id, video_id').eq('run_id', run_id).execute().data or []
ids = [r['id'] for r in rows]

if not ids:
    print("ℹ️ No transactions found for this run", file=sys.stderr)
    print("[]")
    sys.exit(0)

shards = [[] for _ in range(num_workers)]
for i, tid in enumerate(ids):
    shards[i % num_workers].append(tid)

print(json.dumps(shards))
PY
)

if [ -z "$SHARDS" ] || [ "$SHARDS" = "[]" ]; then
  echo "ℹ️ No transactions found for run_id=$RUN_ID"
  exit 0
fi

echo "📦 Sharded transactions across $NUM_WORKERS workers"

PIDS=()
idx=0
for shard in $(echo "$SHARDS" | python3 -u -c 'import sys,json; [print(json.dumps(x)) for x in json.load(sys.stdin)]'); do
  idx=$((idx+1))
  (
    echo "$shard" | WORKER_IDX=$idx python3 -u - <<'PY'
import os, sys, json, logging
sys.path.insert(0, '.')
from integrations.db_supabase import Supa
from config import Settings
from services.processing_service import ProcessingService
from worker.adapter import grade_transactions
from worker.pipeline import upsert_grades
from dotenv import load_dotenv

load_dotenv()
worker_idx = os.environ.get('WORKER_IDX', '0')
logging.basicConfig(level=logging.INFO, format=f'[Worker {worker_idx}] %(levelname)s: %(message)s', stream=sys.stdout, force=True)

s = Settings()
db = Supa(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)
processing = ProcessingService(db, s)

shard = json.load(sys.stdin)
if not shard:
    print("ℹ️ Empty shard; skipping")
    sys.exit(0)

# Fetch full rows for grading
tx_rows = db.client.table('transactions').select('*').in_('id', shard).limit(2).execute().data or []

# Infer location from first video
location_id = None
try:
    if tx_rows:
        vid = db.client.table('videos').select('location_id').eq('id', tx_rows[0]['video_id']).limit(1).execute().data
        if vid:
            location_id = vid[0]['location_id']
except Exception:
    pass

print(f"📊 Shard size: {len(tx_rows)}. Starting grading (location={location_id})...")
grades = grade_transactions(tx_rows, db, location_id)
tx_ids = [r['id'] for r in tx_rows]
if tx_ids and grades:
    upsert_grades(db, tx_ids, grades)
    print(f"✅ Graded and upserted {len(tx_ids)} transactions")
else:
    print("ℹ️ No grades generated for this shard")
PY
  ) &
  PIDS+=($!)
done

for pid in "${PIDS[@]}"; do
  wait $pid
done

echo "🎉 Grading complete for run $RUN_ID"


