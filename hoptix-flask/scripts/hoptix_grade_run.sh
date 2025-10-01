#!/bin/bash

# Grade all transactions for a given run_id in parallel workers

echo "📝 Hoptix Grade Run"
echo "===================="

if [ $# -lt 1 ]; then
  echo "❌ Error: run_id required"
  echo "Usage: $0 RUN_ID [NUM_WORKERS]"
  echo "Example: $0 123e4567-e89b-12d3-a456-426614174000 11"
  exit 1
fi

RUN_ID=$1
NUM_WORKERS=${2:-11}

echo "🔄 Run ID: $RUN_ID"
echo "👥 Workers: $NUM_WORKERS"

cd "$(dirname "$0")/.."

# Fetch transactions for the run and shard IDs into N buckets
SHARDS=$(python3 - <<PY
import sys, math, json
sys.path.insert(0, '.')
from integrations.db_supabase import Supa
from config import Settings
from dotenv import load_dotenv

load_dotenv()
s = Settings()
db = Supa(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)

run_id = "$RUN_ID"
num_workers = $NUM_WORKERS

# Get all transaction IDs for this run
res = db.client.table('transactions').select('id, video_id, started_at, ended_at').eq('run_id', run_id).execute()
txs = res.data or []
ids = [t['id'] for t in txs]

if not ids:
    print(json.dumps([]))
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
for shard in $(echo "$SHARDS" | python3 -c 'import sys,json; [print(json.dumps(x)) for x in json.load(sys.stdin)]'); do
  idx=$((idx+1))
  (
    python3 - <<PY
import sys, json, logging
sys.path.insert(0, '.')
from integrations.db_supabase import Supa
from config import Settings
from services.processing_service import ProcessingService
from worker.adapter import grade_transactions
from worker.pipeline import upsert_grades
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='[Worker $idx] %(levelname)s: %(message)s')

s = Settings()
db = Supa(s.SUPABASE_URL, s.SUPABASE_SERVICE_KEY)
processing = ProcessingService(db, s)

shard = json.loads('$shard')
run_id = "$RUN_ID"

if not shard:
    sys.exit(0)

# Fetch full transaction rows for grading input
tx_rows = db.client.table('transactions').select('*').in_('id', shard).execute().data or []
location_id = None
try:
    # infer location from first video's location
    if tx_rows:
        vid = db.client.table('videos').select('location_id').eq('id', tx_rows[0]['video_id']).limit(1).execute().data
        if vid:
            location_id = vid[0]['location_id']
except Exception:
    pass

grades = grade_transactions(tx_rows, db, location_id)
tx_ids = [r['id'] for r in tx_rows]
if tx_ids and grades:
    upsert_grades(db, tx_ids, grades)
    print(f"✅ Graded and upserted {len(tx_ids)} transactions")
else:
    print("ℹ️ No transactions to grade in this shard")
PY
  ) &
  PIDS+=($!)
done

for pid in "${PIDS[@]}"; do
  wait $pid
done

echo "🎉 Grading complete for run $RUN_ID"


