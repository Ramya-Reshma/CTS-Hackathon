from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]

LM_STUDIO_URL = os.getenv("LM_STUDIO_URL", "http://127.0.0.1:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "qwen/qwen3-4b")
JSON_REPORT_PATH = os.getenv("JSON_REPORT_PATH", str(BASE_DIR / "log" / "final_anomaly_report.json"))
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

TIMEOUT_SECONDS = int(os.getenv("LM_TIMEOUT", "300"))
