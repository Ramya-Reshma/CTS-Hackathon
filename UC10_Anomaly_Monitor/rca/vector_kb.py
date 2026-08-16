import json
import os
from pathlib import Path
from typing import Any, Dict, List

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional dependency
    pd = None

try:
    import chromadb
    from chromadb.utils import embedding_functions
except Exception:  # pragma: no cover - optional dependency
    chromadb = None
    embedding_functions = None


class ChromaCaseKB:
    """Persisted ChromaDB-backed knowledge base for claim resolution cases."""

    def __init__(self, kb_path: str | None = None, persist_dir: str | None = None):
        self.kb_path = kb_path or self._default_path()
        self.persist_dir = persist_dir or str(Path(__file__).resolve().parents[2] / "data" / "vector_kb")
        self.collection = None

        workbook_path = self._default_workbook_path()
        if workbook_path and (kb_path is None or not os.path.exists(kb_path)):
            self.cases = self._load_workbook_cases(workbook_path)
            self.kb_path = workbook_path
        else:
            self.cases = self._load_cases(self.kb_path)

        if not self.cases and workbook_path:
            self.cases = self._load_workbook_cases(workbook_path)
            self.kb_path = workbook_path

        if chromadb is not None:
            self._init_collection()

    def _default_path(self) -> str:
        base = Path(__file__).resolve().parents[2]
        candidates = [
            base / "log" / "historical_resolution_cases.json",
            base / "Data" / "historical_resolution_cases.json",
            base / "historical_resolution_cases.json",
        ]
        for path in candidates:
            if path.exists():
                return str(path)
        return str(base / "log" / "historical_resolution_cases.json")

    def _default_workbook_path(self) -> str | None:
        base = Path(__file__).resolve().parents[2]
        candidates = [
            base / "healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx",
            base / "Data" / "healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx",
            base / "log" / "healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx",
        ]
        for path in candidates:
            if path.exists():
                return str(path)
        matches = list(base.glob("**/*RAG*knowledge*base*.xlsx"))
        if matches:
            return str(matches[0])
        return None

    def _is_workbook_source(self) -> bool:
        return bool(self.kb_path) and self.kb_path.lower().endswith(".xlsx")

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

    def _load_workbook_cases(self, workbook_path: str | None) -> List[Dict[str, Any]]:
        if not workbook_path or pd is None or not os.path.exists(workbook_path):
            return []

        try:
            workbook = pd.ExcelFile(workbook_path)
        except Exception:
            return []

        rows: List[Dict[str, Any]] = []
        for sheet_name in workbook.sheet_names:
            try:
                df = pd.read_excel(workbook_path, sheet_name=sheet_name)
            except Exception:
                continue
            if df.empty:
                continue
            for _, row in df.iterrows():
                case = row.to_dict()
                normalized = {}
                for key, value in case.items():
                    normalized_key = str(key).strip()
                    normalized_value = "" if pd.isna(value) else value
                    normalized[normalized_key] = normalized_value

                anomaly_name = normalized.get("Anomaly_Name") or normalized.get("anomaly_name") or ""
                root_cause = normalized.get("Root_Cause") or normalized.get("root_cause") or ""
                recommendations = normalized.get("Recommended_Fix") or normalized.get("recommended_fix") or ""
                applicable_types = normalized.get("Applicable_Record_Types") or normalized.get("applicable_record_types") or ""
                record_types = [part.strip() for part in str(applicable_types).split(";") if part.strip()]

                kb_id = normalized.get("KB_ID") or normalized.get("KBId") or normalized.get("id") or f"kb_{len(rows)}"
                document = {
                    "incident_id": str(kb_id),
                    "record_type": record_types[0] if record_types else "General",
                    "status": "Known issue",
                    "denial_reason_code": normalized.get("Anomaly_Type") or normalized.get("anomaly_type") or "",
                    "auth_required_flag": "",
                    "days_supply": "",
                    "quantity_dispensed": "",
                    "billed_amount": "",
                    "allowed_amount": "",
                    "paid_amount": "",
                    "root_cause": root_cause,
                    "resolution_used": recommendations,
                    "recommended_actions": [recommendations] if recommendations else [],
                    "impact": normalized.get("Typical_Severity") or normalized.get("typical_severity") or "",
                    "confidence": 0.8,
                    "document_text": normalized.get("RAG_Text") or normalized.get("rag_text") or " ".join([
                        str(anomaly_name),
                        str(root_cause),
                        str(recommendations),
                        str(applicable_types),
                    ]),
                    "source": "workbook",
                    "anomaly_name": anomaly_name,
                    "anomaly_type": normalized.get("Anomaly_Type") or normalized.get("anomaly_type") or "",
                    "sub_type": normalized.get("Sub_Type") or normalized.get("sub_type") or "",
                    "primary_signals": normalized.get("Primary_Signals") or normalized.get("primary_signals") or "",
                    "applicable_record_types": applicable_types,
                }
                rows.append(document)
        return rows

    def _build_case_document(self, case: Dict[str, Any]) -> str:
        summary = {
            "incident_id": case.get("incident_id") or case.get("Record_ID") or case.get("KB_ID") or "",
            "record_type": case.get("record_type") or case.get("Record_Type") or case.get("Applicable_Record_Types") or "",
            "status": case.get("status") or case.get("Status") or "",
            "denial_reason_code": case.get("denial_reason_code") or case.get("Denial_Reason_Code") or case.get("denial_reason") or case.get("Anomaly_Type") or "",
            "auth_required_flag": case.get("auth_required_flag") or case.get("Auth_Required_Flag") or "",
            "days_supply": case.get("days_supply") or case.get("Days_Supply") or "",
            "quantity_dispensed": case.get("quantity_dispensed") or case.get("Quantity_Dispensed") or "",
            "billed_amount": case.get("billed_amount") or case.get("Billed_Amount") or "",
            "allowed_amount": case.get("allowed_amount") or case.get("Allowed_Amount") or "",
            "paid_amount": case.get("paid_amount") or case.get("Paid_Amount") or "",
            "root_cause": case.get("root_cause") or case.get("Root_Cause") or "",
            "resolution_used": case.get("resolution_used") or case.get("resolution") or case.get("Recommended_Fix") or "",
            "recommended_actions": case.get("recommended_actions") or case.get("recommendations") or ([case.get("Recommended_Fix")] if case.get("Recommended_Fix") else []),
            "impact": case.get("impact") or case.get("Typical_Severity") or "",
            "anomaly_name": case.get("anomaly_name") or case.get("Anomaly_Name") or "",
            "anomaly_type": case.get("anomaly_type") or case.get("Anomaly_Type") or "",
            "sub_type": case.get("sub_type") or case.get("Sub_Type") or "",
            "document_text": case.get("document_text") or case.get("RAG_Text") or "",
        }
        return json.dumps(summary, ensure_ascii=False)

    def _build_query_text(self, current_record: Dict[str, Any]) -> str:
        query_fields = {
            "record_type": current_record.get("record_type") or current_record.get("Record_Type") or "",
            "status": current_record.get("status") or current_record.get("Status") or "",
            "denial_reason_code": current_record.get("denial_reason_code") or current_record.get("Denial_Reason_Code") or current_record.get("denial_reason") or "",
            "auth_required_flag": current_record.get("auth_required_flag") or current_record.get("Auth_Required_Flag") or "",
            "days_supply": current_record.get("days_supply") or current_record.get("Days_Supply") or "",
            "quantity_dispensed": current_record.get("quantity_dispensed") or current_record.get("Quantity_Dispensed") or "",
            "billed_amount": current_record.get("billed_amount") or current_record.get("Billed_Amount") or "",
            "allowed_amount": current_record.get("allowed_amount") or current_record.get("Allowed_Amount") or "",
            "paid_amount": current_record.get("paid_amount") or current_record.get("Paid_Amount") or "",
            "evidence": current_record.get("evidence") or [],
            "likely_root_cause": current_record.get("likely_root_cause") or current_record.get("root_cause") or "",
            "rag_text": current_record.get("rag_text") or current_record.get("document_text") or "",
            "anomaly_name": current_record.get("anomaly_name") or current_record.get("Anomaly_Name") or "",
        }
        return json.dumps(query_fields, ensure_ascii=False)

    def _init_collection(self):
        if chromadb is None or embedding_functions is None:
            self.collection = None
            return

        os.makedirs(self.persist_dir, exist_ok=True)
        client = chromadb.PersistentClient(path=self.persist_dir)

        try:
            embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        except Exception:
            embedding_fn = embedding_functions.DefaultEmbeddingFunction()

        collection_name = "claims_resolution_kb"
        try:
            self.collection = client.get_collection(name=collection_name)
        except Exception:
            self.collection = None

        if self.collection is None:
            self.collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=embedding_fn,
            )

        if self._is_workbook_source() and self.collection.count() > 0:
            try:
                client.delete_collection(name=collection_name)
            except Exception:
                pass
            self.collection = client.get_or_create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=embedding_fn,
            )

        if self.collection.count() == 0 and self.cases:
            self.index_cases(self.cases)

    def index_cases(self, cases: List[Dict[str, Any]]) -> None:
        if self.collection is None:
            return

        documents = []
        metadatas = []
        ids = []

        for index, case in enumerate(cases):
            doc_text = self._build_case_document(case)
            doc_id = str(case.get("incident_id") or case.get("Record_ID") or case.get("KB_ID") or case.get("id") or f"case_{index}")
            documents.append(doc_text)
            ids.append(doc_id)
            metadatas.append({
                "incident_id": case.get("incident_id") or case.get("Record_ID") or case.get("KB_ID") or "",
                "record_type": case.get("record_type") or case.get("Record_Type") or case.get("Applicable_Record_Types") or "",
                "status": case.get("status") or case.get("Status") or "",
                "denial_reason_code": case.get("denial_reason_code") or case.get("Denial_Reason_Code") or case.get("denial_reason") or case.get("Anomaly_Type") or "",
                "auth_required_flag": case.get("auth_required_flag") or case.get("Auth_Required_Flag") or "",
                "root_cause": case.get("root_cause") or case.get("Root_Cause") or "",
                "resolution_used": case.get("resolution_used") or case.get("resolution") or case.get("Recommended_Fix") or "",
                "recommended_actions": json.dumps(case.get("recommended_actions") or case.get("recommendations") or ([case.get("Recommended_Fix")] if case.get("Recommended_Fix") else []), ensure_ascii=False),
                "impact": case.get("impact") or case.get("Typical_Severity") or "",
                "confidence": case.get("confidence") or 0.0,
                "source": case.get("source") or "",
                "anomaly_name": case.get("anomaly_name") or case.get("Anomaly_Name") or "",
            })

        if documents:
            self.collection.upsert(documents=documents, ids=ids, metadatas=metadatas)

    def search(self, current_record: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        if self.collection is None or self.collection.count() == 0:
            return []

        query_text = self._build_query_text(current_record)
        results = self.collection.query(
            query_texts=[query_text],
            n_results=min(limit, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits: List[Dict[str, Any]] = []
        for doc, meta, distance in zip(
            results.get("documents", [[]])[0],
            results.get("metadatas", [[]])[0],
            results.get("distances", [[]])[0],
        ):
            payload = dict(meta or {})
            payload["document"] = doc
            payload["distance"] = distance
            payload["recommended_actions"] = json.loads(payload.get("recommended_actions", "[]")) if isinstance(payload.get("recommended_actions"), str) else payload.get("recommended_actions", [])
            payload["confidence"] = payload.get("confidence", 0.0)
            hits.append(payload)
        return hits
