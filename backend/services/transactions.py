from typing import List, Dict, Any
from datetime import datetime

def format_transactions(transcript_segments: List[Dict[str, Any]], run_id: str, audio_id: str) -> List[Dict[str, Any]]:
    transactions = []
    for i, segment in enumerate(transcript_segments):
        transaction = {
            'run_id': run_id,
            'audio_id': audio_id,
            'start_time': segment['start'],
            'end_time': segment['end'],
            'transcript': segment['text'],
            'created_at': datetime.now().isoformat()
        }
        transactions.append(transaction)
    return transactions