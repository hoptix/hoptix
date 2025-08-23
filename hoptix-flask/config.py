import os
from dataclasses import dataclass

@dataclass
class Settings:
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-2")
    RAW_BUCKET: str = os.getenv("RAW_BUCKET", "hoptix-raw-devprod")
    PART_SIZE_BYTES: int = int(os.getenv("PART_SIZE_BYTES", str(64 * 1024 * 1024)))  # 64MB
    URL_TTL_SECONDS: int = int(os.getenv("URL_TTL_SECONDS", "1800"))                 # 30min

    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")