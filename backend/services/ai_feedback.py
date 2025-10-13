from services.database import Supa
from config import Settings, Prompts
from openai import OpenAI
from utils.helpers import json_or_none
import json
import re

settings = Settings()
prompts = Prompts()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

db = Supa()


def validate_and_clean_transaction_ids(feedback_dict):
    """
    Validate and clean transaction IDs in the feedback dictionary.
    Removes malformed UUIDs that would cause database errors.
    """
    if not feedback_dict or not isinstance(feedback_dict, dict):
        return feedback_dict

    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
    cleaned_count = 0

    # Clean transaction_ids in top_issues
    if 'top_issues' in feedback_dict and isinstance(feedback_dict['top_issues'], list):
        for issue in feedback_dict['top_issues']:
            if 'transaction_ids' in issue and isinstance(issue['transaction_ids'], list):
                original_count = len(issue['transaction_ids'])
                issue['transaction_ids'] = [tid for tid in issue['transaction_ids']
                                           if isinstance(tid, str) and uuid_pattern.match(tid.strip())]
                removed = original_count - len(issue['transaction_ids'])
                if removed > 0:
                    cleaned_count += removed
                    print(f"⚠️ Removed {removed} invalid transaction IDs from issue: {issue.get('issue', 'unknown')[:50]}")

    # Clean transaction_ids in top_strengths
    if 'top_strengths' in feedback_dict and isinstance(feedback_dict['top_strengths'], list):
        for strength in feedback_dict['top_strengths']:
            if 'transaction_ids' in strength and isinstance(strength['transaction_ids'], list):
                original_count = len(strength['transaction_ids'])
                strength['transaction_ids'] = [tid for tid in strength['transaction_ids']
                                              if isinstance(tid, str) and uuid_pattern.match(tid.strip())]
                removed = original_count - len(strength['transaction_ids'])
                if removed > 0:
                    cleaned_count += removed
                    print(f"⚠️ Removed {removed} invalid transaction IDs from strength: {strength.get('strength', 'unknown')[:50]}")

    if cleaned_count > 0:
        print(f"🧹 Total cleaned: {cleaned_count} invalid transaction IDs")

    return feedback_dict


def get_ai_feedback(run_id=None, operator_id=None):

    print(f"🔍 Getting feedback for operator {operator_id}...")

    #get the operator feedback from the database for the past month
    operator_feedback = db.get_operator_feedback_raw(run_id, operator_id)
    print(f"📊 Found {len(operator_feedback)} feedback records")

    if not operator_feedback:
        print("⚠️ No feedback data found, returning None")
        return None

    # Limit feedback to last 50 records to avoid overwhelming the AI
    if len(operator_feedback) > 50:
        operator_feedback = operator_feedback[-50:]
        print(f"📝 Limited to last 50 feedback records")

    print(f"🤖 Calling AI model: {settings.AI_FEEDBACK_MODEL}")

    #use the operator feedback to generate a feedback report
    resp = client.responses.create(
        model=settings.AI_FEEDBACK_MODEL,
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompts.AI_FEEDBACK_PROMPT.format(feedback_block=operator_feedback)}]}],
        store=False,
        text={"format": {"type": "text"}},
        reasoning={"effort": "medium", "summary": "detailed"},  # Using detailed summary as required by gpt-5-nano
    )

    print(f"✅ AI response received")
    feedback_dict = json_or_none(resp.output[1].content[0].text)

    # Validate and clean transaction IDs before storing
    if feedback_dict:
        feedback_dict = validate_and_clean_transaction_ids(feedback_dict)
        return json.dumps(feedback_dict)
    return None


    