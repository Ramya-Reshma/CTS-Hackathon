import json
from typing import List, Dict, Any
from pathlib import Path
from UC10_Anomaly_Monitor.config import settings


def _load_report(path: str = None) -> List[Dict[str, Any]]:
    path = path or settings.JSON_REPORT_PATH
    p = Path(path)
    if not p.exists():
        return []
    return json.loads(p.read_text())


def get_record_details(record_id: str, path: str = None) -> Dict[str, Any]:
    report = _load_report(path)
    for rec in report:
        if rec.get("Record_ID") == record_id or rec.get("Record_ID", "").upper() == record_id.upper():
            return rec
    raise KeyError(f"Record {record_id} not found in report.")


def get_provider_history(provider_npi: str, limit: int = 10, path: str = None) -> List[Dict[str, Any]]:
    report = _load_report(path)
    hits = [r for r in report if r.get("Provider_NPI") == provider_npi]
    return hits[:limit]
