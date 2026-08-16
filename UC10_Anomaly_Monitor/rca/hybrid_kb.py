import json
import os
from pathlib import Path
from typing import Any, Dict, List, Tuple


class HistoricalCaseKB:
    """Hybrid historical KB with exact filters + lightweight semantic similarity scoring."""

    def __init__(self, kb_path: str | None = None):
        self.kb_path = kb_path or self._default_path()
        self.cases = self._load_cases(self.kb_path)

    def _default_path(self) -> str:
        base = Path(__file__).resolve().parents[2]
        candidates = [
            base / "log" / "historical_resolution_cases.json",
            base / "Data" / "historical_resolution_cases.json",
            base / "historical_resolution_cases.json",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return str(base / "log" / "historical_resolution_cases.json")

    def _load_cases(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            if isinstance(payload, dict):
                if "cases" in payload:
                    return payload["cases"]
                if "historical_cases" in payload:
                    return payload["historical_cases"]
                return [payload]
            if isinstance(payload, list):
                return payload
        except Exception:
            return []
        return []

    def _to_float(self, value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

    def _as_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)

    def _semantic_tokens(self, text: str) -> set:
        if not text:
            return set()
        cleaned = ''.join(ch.lower() for ch in text if ch.isalnum() or ch.isspace() or ch in ['-', '_'])
        return set(cleaned.split())

    def _semantic_overlap(self, current: Dict[str, Any], historical: Dict[str, Any]) -> float:
        current_text = self._as_text({
            "record_type": current.get("record_type") or current.get("Record_Type"),
            "status": current.get("status") or current.get("Status"),
            "denial_reason_code": current.get("denial_reason_code") or current.get("Denial_Reason_Code") or current.get("denial_reason"),
            "root_cause": current.get("likely_root_cause") or current.get("root_cause") or current.get("summary"),
            "evidence": current.get("evidence") or [],
        })

        hist_text = self._as_text({
            "record_type": historical.get("record_type") or historical.get("Record_Type"),
            "status": historical.get("status") or historical.get("Status"),
            "denial_reason_code": historical.get("denial_reason_code") or historical.get("Denial_Reason_Code") or historical.get("denial_reason"),
            "root_cause": historical.get("root_cause") or historical.get("resolution_used") or historical.get("summary"),
            "recommended_actions": historical.get("recommended_actions") or [],
        })

        cur_tokens = self._semantic_tokens(current_text)
        hist_tokens = self._semantic_tokens(hist_text)
        if not cur_tokens or not hist_tokens:
            return 0.0
        overlap = len(cur_tokens & hist_tokens)
        total = len(cur_tokens | hist_tokens)
        return overlap / total if total else 0.0

    def _match_score(self, current: Dict[str, Any], historical: Dict[str, Any]) -> float:
        score = 0.0

        current_type = (current.get("record_type") or current.get("Record_Type") or "").upper()
        hist_type = (historical.get("record_type") or historical.get("Record_Type") or "").upper()
        if current_type and hist_type and current_type == hist_type:
            score += 0.30

        current_status = (current.get("status") or current.get("Status") or "").upper()
        hist_status = (historical.get("status") or historical.get("Status") or "").upper()
        if current_status and hist_status and current_status == hist_status:
            score += 0.20

        current_reason = str(current.get("denial_reason_code") or current.get("Denial_Reason_Code") or current.get("denial_reason") or "").upper()
        hist_reason = str(historical.get("denial_reason_code") or historical.get("Denial_Reason_Code") or historical.get("denial_reason") or "").upper()
        if current_reason and hist_reason and current_reason == hist_reason:
            score += 0.25
        elif current_reason and hist_reason and current_reason in hist_reason or hist_reason in current_reason:
            score += 0.12

        current_auth = str(current.get("auth_required_flag") or current.get("Auth_Required_Flag") or "").upper()
        hist_auth = str(historical.get("auth_required_flag") or historical.get("Auth_Required_Flag") or "").upper()
        if current_auth and hist_auth and current_auth == hist_auth:
            score += 0.10

        fields = ["days_supply", "quantity_dispensed", "billed_amount", "allowed_amount", "paid_amount"]
        for field in fields:
            current_val = self._to_float(current.get(field) or current.get(field.capitalize()) or current.get(field.replace('_', ' ')))
            hist_val = self._to_float(historical.get(field) or historical.get(field.capitalize()) or historical.get(field.replace('_', ' ')))
            if current_val > 0 and hist_val > 0:
                ratio = min(current_val, hist_val) / max(current_val, hist_val)
                score += 0.05 * ratio

        if bool(current.get("iso_anomaly") or current.get("ISO_Is_Anomaly") or False) == bool(historical.get("iso_anomaly") or historical.get("ISO_Is_Anomaly") or False):
            score += 0.05

        if bool(current.get("correlation_anomaly") or current.get("Correlation_Anomaly") or False) == bool(historical.get("correlation_anomaly") or historical.get("Correlation_Anomaly") or False):
            score += 0.05

        score += self._semantic_overlap(current, historical) * 0.35
        return min(score, 1.0)

    def search(self, current_record: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        ranked = []
        for case in self.cases:
            score = self._match_score(current_record, case)
            if score <= 0:
                continue
            ranked.append({
                "incident_id": case.get("incident_id") or case.get("Record_ID") or "",
                "record_type": case.get("record_type") or case.get("Record_Type") or "",
                "status": case.get("status") or case.get("Status") or "",
                "denial_reason_code": case.get("denial_reason_code") or case.get("Denial_Reason_Code") or case.get("denial_reason") or "",
                "auth_required_flag": case.get("auth_required_flag") or case.get("Auth_Required_Flag") or "",
                "root_cause": case.get("root_cause") or "",
                "resolution_used": case.get("resolution_used") or case.get("resolution") or "",
                "recommended_actions": case.get("recommended_actions") or case.get("recommendations") or [],
                "score": round(score, 4),
                **case,
            })

        ranked.sort(key=lambda x: x["score"], reverse=True)
        return ranked[:limit]


if __name__ == "__main__":
    kb = HistoricalCaseKB()
    print(f"Loaded {len(kb.cases)} historical cases.")
