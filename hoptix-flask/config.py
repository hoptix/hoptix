import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

@dataclass
class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    RAW_BUCKET: str = os.getenv("RAW_BUCKET", "hoptix-raw-devprod")
    DERIV_BUCKET: str = os.getenv("DERIV_BUCKET", "hoptix-deriv-devprod")
    
    # SQS Configuration
    SQS_QUEUE_URL: str = os.getenv("SQS_QUEUE_URL", "")
    SQS_DLQ_URL: str = os.getenv("SQS_DLQ_URL", "")  # Dead Letter Queue
    SQS_VISIBILITY_TIMEOUT: int = int(os.getenv("SQS_VISIBILITY_TIMEOUT", "1800"))  # 30 minutes
    SQS_WAIT_TIME: int = int(os.getenv("SQS_WAIT_TIME", "20"))  # Long polling

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    ASR_MODEL: str = os.getenv("ASR_MODEL", "gpt-4o-transcribe")
    STEP1_MODEL: str = os.getenv("STEP1_MODEL", "o3")
    STEP2_MODEL: str = os.getenv("STEP2_MODEL", "o3")

    # where to load menu/prompts jsons from (local files). All optional.
    PROMPTS_DIR: str = os.getenv("PROMPTS_DIR", "./prompts")
    ITEMS_JSON: str = os.getenv("ITEMS_JSON", "items.json")
    MEALS_JSON: str = os.getenv("MEALS_JSON", "meals.json")
    UPSELLING_JSON: str = os.getenv("UPSELLING_JSON", "upselling.json")
    UPSIZING_JSON: str = os.getenv("UPSIZING_JSON", "upsizing.json")
    ADDONS_JSON: str = os.getenv("ADDONS_JSON", "addons.json")