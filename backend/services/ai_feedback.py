from services.database import Supa
from config import Settings, Prompts
from openai import OpenAI
from utils.helpers import json_or_none

settings = Settings()
prompts = Prompts()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

db = Supa() 


def get_ai_feedback(operator_id):
    print(f"🔍 Getting feedback for operator {operator_id}...")
    
    #get the operator feedback from the database for the past month
    operator_feedback = db.get_operator_feedback_raw(operator_id)
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
    return json_or_none(resp.output[1].content[0].text)


    