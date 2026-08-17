import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parents[2]

# Bedrock Configuration (Primary)
USE_BEDROCK = os.getenv("USE_BEDROCK", "true").lower() == "true"
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "qwen2p5-coder-32b-instruct-v0-1")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# LM Studio Configuration (Fallback)
LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "qwen/qwen3-4b")

# Common Configuration
JSON_REPORT_PATH = os.getenv("JSON_REPORT_PATH", str(BASE_DIR / "log" / "final_anomaly_report.json"))
TIMEOUT_SECONDS = int(os.getenv("LM_TIMEOUT", "300"))
