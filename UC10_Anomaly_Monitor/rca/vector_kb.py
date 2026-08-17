import json
import os
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import pandas as pd
except Exception:
    pd = None

try:
    import chromadb
    from chromadb.utils import embedding_functions
except Exception:
    chromadb = None
    embedding_functions = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


class ChromaCaseKB:
    """
    ChromaDB vector store backed knowledge base for healthcare claims anomalies.
    Uses Sentence Transformer 'all-MiniLM-L6-v2' with cosine similarity.
    """

    def __init__(self, kb_path: Optional[str] = None, persist_dir: Optional[str] = None):
        self.base_dir = Path(__file__).resolve().parents[2]
        self.kb_path = kb_path or self._default_kb_path()
        self.persist_dir = persist_dir or str(self.base_dir / "data" / "vector_kb")
        self.collection_name = "claims_resolution_kb"
        self.collection = None
        self.cases: List[Dict[str, Any]] = []
        self._st_model = None

        # Load knowledge base records (supports Excel workbook and JSON fallback)
        if self.kb_path and self.kb_path.lower().endswith((".xlsx", ".xls")):
            self.cases = self._load_workbook_cases(self.kb_path)
        else:
            self.cases = self._load_json_cases(self.kb_path)

        if not self.cases:
            # Try finding the workbook in standard project paths
            wb_path = self._default_kb_path()
            if wb_path and wb_path.lower().endswith((".xlsx", ".xls")):
                self.cases = self._load_workbook_cases(wb_path)
                self.kb_path = wb_path

        # Initialize ChromaDB collection if chromadb is installed
        if chromadb is not None:
            try:
                self._init_chroma()
            except Exception as e:
                print(f"[VectorKB] ChromaDB init warning: {e}")
                self.collection = None

    def _default_kb_path(self) -> str:
        candidates = [
            self.base_dir / "healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx",
            self.base_dir / "Data" / "healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx",
            self.base_dir / "log" / "historical_resolution_cases.json",
            self.base_dir / "Data" / "historical_resolution_cases.json",
        ]
        for c in candidates:
            if c.exists():
                return str(c)
        matches = list(self.base_dir.glob("**/*RAG*knowledge*base*.xlsx"))
        if matches:
            return str(matches[0])
        return str(self.base_dir / "healthcare_claims_anomaly_RAG_knowledge_base_REBUILT.xlsx")

    def _load_workbook_cases(self, path: str) -> List[Dict[str, Any]]:
        if pd is None or not os.path.exists(path):
            return []
        try:
            workbook = pd.ExcelFile(path)
            cases: List[Dict[str, Any]] = []
            for sheet in workbook.sheet_names:
                df = pd.read_excel(path, sheet_name=sheet)
                if df.empty:
                    continue
                for _, row in df.iterrows():
                    rec = row.to_dict()
                    cleaned = {str(k).strip(): ("" if pd.isna(v) else v) for k, v in rec.items()}
                    
                    kb_id = cleaned.get("KB_ID") or cleaned.get("KBId") or f"KB_{len(cases)+1:04d}"
                    anom_type = cleaned.get("Anomaly_Type") or cleaned.get("anomaly_type") or "Healthcare Anomaly"
                    sub_type = cleaned.get("Sub_Type") or cleaned.get("sub_type") or "General"
                    anom_name = cleaned.get("Anomaly_Name") or cleaned.get("anomaly_name") or ""
                    root_cause = cleaned.get("Root_Cause") or cleaned.get("root_cause") or ""
                    rec_fix = cleaned.get("Recommended_Fix") or cleaned.get("recommended_fix") or ""
                    signals = cleaned.get("Primary_Signals") or cleaned.get("primary_signals") or ""
                    severity = cleaned.get("Typical_Severity") or cleaned.get("typical_severity") or "Medium"
                    app_types = cleaned.get("Applicable_Record_Types") or cleaned.get("applicable_record_types") or "Medical; Pharmacy; Authorization"
                    rag_text = cleaned.get("RAG_Text") or cleaned.get("rag_text") or (
                        f"Anomaly Type: {anom_type} | Sub-Type: {sub_type} | Anomaly: {anom_name} | "
                        f"Root Cause: {root_cause} | Recommended Fix: {rec_fix} | Primary Signals: {signals} | "
                        f"Typical Severity: {severity} | Applicable Record Types: {app_types}"
                    )

                    doc_entry = {
                        "KB_ID": str(kb_id),
                        "Anomaly_Type": str(anom_type),
                        "Sub_Type": str(sub_type),
                        "Anomaly_Name": str(anom_name),
                        "Root_Cause": str(root_cause),
                        "Recommended_Fix": str(rec_fix),
                        "Primary_Signals": str(signals),
                        "Typical_Severity": str(severity),
                        "Applicable_Record_Types": str(app_types),
                        "RAG_Text": str(rag_text)
                    }
                    cases.append(doc_entry)
            return cases
        except Exception as e:
            print(f"[VectorKB] Error loading workbook: {e}")
            return []

    def _load_json_cases(self, path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = data.get("cases") or data.get("historical_cases") or [data]
            if not isinstance(data, list):
                return []
            
            norm_cases = []
            for i, item in enumerate(data):
                kb_id = item.get("KB_ID") or item.get("incident_id") or f"KB_{i+1:04d}"
                norm_cases.append({
                    "KB_ID": str(kb_id),
                    "Anomaly_Type": str(item.get("Anomaly_Type") or item.get("anomaly_type") or "General"),
                    "Sub_Type": str(item.get("Sub_Type") or item.get("sub_type") or ""),
                    "Anomaly_Name": str(item.get("Anomaly_Name") or item.get("anomaly_name") or ""),
                    "Root_Cause": str(item.get("Root_Cause") or item.get("root_cause") or ""),
                    "Recommended_Fix": str(item.get("Recommended_Fix") or item.get("resolution_used") or item.get("recommended_fix") or ""),
                    "Primary_Signals": str(item.get("Primary_Signals") or item.get("primary_signals") or ""),
                    "Typical_Severity": str(item.get("Typical_Severity") or item.get("impact") or item.get("severity") or "Medium"),
                    "Applicable_Record_Types": str(item.get("Applicable_Record_Types") or item.get("record_type") or ""),
                    "RAG_Text": str(item.get("RAG_Text") or item.get("document_text") or item.get("root_cause") or "")
                })
            return norm_cases
        except Exception as e:
            print(f"[VectorKB] Error loading JSON cases: {e}")
            return []

    def _get_sentence_transformer(self):
        if self._st_model is None and SentenceTransformer is not None:
            try:
                self._st_model = SentenceTransformer("all-MiniLM-L6-v2")
            except Exception as e:
                print(f"[VectorKB] SentenceTransformer load error: {e}")
                self._st_model = None
        return self._st_model

    def _init_chroma(self):
        os.makedirs(self.persist_dir, exist_ok=True)
        client = chromadb.PersistentClient(path=self.persist_dir)

        # Build SentenceTransformer embedding function with all-MiniLM-L6-v2
        try:
            emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        except Exception:
            emb_fn = embedding_functions.DefaultEmbeddingFunction()

        try:
            self.collection = client.get_collection(name=self.collection_name, embedding_function=emb_fn)
            sample = self.collection.get(limit=1, include=["metadatas"])
            if sample and sample.get("metadatas") and len(sample["metadatas"]) > 0:
                if "KB_ID" not in sample["metadatas"][0]:
                    print("[VectorKB] Migrating ChromaDB collection to standard KB_ID metadata schema...")
                    client.delete_collection(name=self.collection_name)
                    self.collection = None
        except Exception:
            self.collection = None

        if self.collection is None:
            self.collection = client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
                embedding_function=emb_fn
            )
            if self.cases:
                self.index_cases(self.cases)
        elif self.collection.count() == 0 and self.cases:
            self.index_cases(self.cases)

    def index_cases(self, cases: List[Dict[str, Any]]) -> None:
        if self.collection is None or not cases:
            return

        documents = []
        metadatas = []
        ids = []

        for idx, c in enumerate(cases):
            doc_id = str(c.get("KB_ID") or f"KB_{idx+1:04d}")
            doc_text = c.get("RAG_Text") or (
                f"{c.get('Anomaly_Name', '')} {c.get('Anomaly_Type', '')} {c.get('Root_Cause', '')} "
                f"{c.get('Primary_Signals', '')} {c.get('Recommended_Fix', '')}"
            )
            documents.append(doc_text)
            ids.append(doc_id)
            metadatas.append({
                "KB_ID": str(c.get("KB_ID", doc_id)),
                "Anomaly_Type": str(c.get("Anomaly_Type", "")),
                "Sub_Type": str(c.get("Sub_Type", "")),
                "Anomaly_Name": str(c.get("Anomaly_Name", "")),
                "Root_Cause": str(c.get("Root_Cause", "")),
                "Recommended_Fix": str(c.get("Recommended_Fix", "")),
                "Primary_Signals": str(c.get("Primary_Signals", "")),
                "Typical_Severity": str(c.get("Typical_Severity", "")),
                "Applicable_Record_Types": str(c.get("Applicable_Record_Types", "")),
                "RAG_Text": str(doc_text)
            })

        # Batch upsert to avoid large transaction limits
        batch_size = 100
        for i in range(0, len(documents), batch_size):
            self.collection.upsert(
                documents=documents[i:i+batch_size],
                metadatas=metadatas[i:i+batch_size],
                ids=ids[i:i+batch_size]
            )
        print(f"[VectorKB] Indexed {len(documents)} knowledge records in ChromaDB collection '{self.collection_name}'.")

    def _build_query_text(self, record: Dict[str, Any]) -> str:
        """Construct semantic retrieval query from compact evidence."""
        rec_type = record.get("record_type") or record.get("Record_Type") or ""
        anom_type = record.get("anomaly_type") or ""
        primary_sig = record.get("primary_signal") or ""
        
        # Check nested structures from compact evidence
        iso = record.get("isolation_forest", {})
        corr = record.get("correlation", {})
        stat = record.get("statistical", {})
        
        iso_flag = iso.get("is_anomaly", record.get("ISO_Is_Anomaly", False))
        iso_score = iso.get("raw_score", record.get("ISO_Raw_Score"))
        corr_flag = corr.get("anomaly", record.get("Correlation_Anomaly", False))
        corr_res = corr.get("residual", record.get("Correlation_Residual"))
        qs_flag = corr.get("quantity_supply_anomaly", record.get("Quantity_Supply_Anomaly", False))
        qs_res = corr.get("quantity_supply_residual", record.get("Quantity_Supply_Residual"))
        affected = stat.get("affected_fields", record.get("Stat_Anomaly_Fields", []))

        status = record.get("status") or ""
        denial = record.get("denial_reason_code") or ""

        query_parts = [
            f"Record Type: {rec_type}",
            f"Anomaly Type: {anom_type}",
            f"Primary Signal: {primary_sig}",
        ]
        if status:
            query_parts.append(f"Status: {status}")
        if denial:
            query_parts.append(f"Denial Reason: {denial}")
        if iso_flag:
            query_parts.append(f"Isolation Forest Anomaly score {iso_score}")
        if corr_flag:
            query_parts.append(f"Correlation Breakdown Paid vs Allowed residual {corr_res}")
        if qs_flag:
            query_parts.append(f"Quantity vs Days Supply residual {qs_res}")
        if affected:
            query_parts.append(f"Statistical outliers in {affected}")

        return " | ".join(query_parts)

    def search(self, current_record: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve the top-K most relevant healthcare knowledge records.
        Prioritizes ChromaDB vector search; falls back to MiniLM direct cosine similarity or text matching.
        """
        if not self.cases:
            return []

        query_str = self._build_query_text(current_record)

        # 1. ChromaDB vector search
        if self.collection is not None and self.collection.count() > 0:
            try:
                n_results = min(limit, self.collection.count())
                results = self.collection.query(
                    query_texts=[query_str],
                    n_results=n_results,
                    include=["metadatas", "documents", "distances"]
                )
                hits: List[Dict[str, Any]] = []
                docs = results.get("documents", [[]])[0]
                metas = results.get("metadatas", [[]])[0]
                distances = results.get("distances", [[]])[0]

                for doc, meta, dist in zip(docs, metas, distances):
                    hit = dict(meta or {})
                    # In cosine distance: similarity = 1.0 - distance
                    sim = round(max(0.0, 1.0 - float(dist)), 4) if dist is not None else 0.8
                    hit["similarity"] = sim
                    hit["distance"] = dist
                    hits.append(hit)
                if hits:
                    return hits
            except Exception as e:
                print(f"[VectorKB] ChromaDB query failed: {e}")

        # 2. Fallback: Direct SentenceTransformer encoding & Cosine Similarity
        model = self._get_sentence_transformer()
        if model is not None:
            try:
                import numpy as np
                q_emb = model.encode([query_str])[0]
                texts = [c.get("RAG_Text", "") for c in self.cases]
                doc_embs = model.encode(texts)
                
                # Compute cosine similarities
                q_norm = np.linalg.norm(q_emb)
                doc_norms = np.linalg.norm(doc_embs, axis=1)
                sims = np.dot(doc_embs, q_emb) / (doc_norms * q_norm + 1e-9)
                
                top_indices = np.argsort(sims)[::-1][:limit]
                hits = []
                for idx in top_indices:
                    case_copy = dict(self.cases[idx])
                    case_copy["similarity"] = round(float(sims[idx]), 4)
                    hits.append(case_copy)
                return hits
            except Exception as e:
                print(f"[VectorKB] Direct SentenceTransformer embedding search failed: {e}")

        # 3. Fallback: Keyword token overlap scoring
        query_tokens = set(query_str.lower().split())
        scored = []
        for case in self.cases:
            target_text = f"{case.get('Anomaly_Name', '')} {case.get('Anomaly_Type', '')} {case.get('Primary_Signals', '')} {case.get('Applicable_Record_Types', '')}".lower()
            overlap = sum(1 for t in query_tokens if t in target_text and len(t) > 2)
            score = round(overlap / max(1, len(query_tokens)), 4)
            scored.append((score, case))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_cases = []
        for score, case in scored[:limit]:
            c = dict(case)
            c["similarity"] = score
            top_cases.append(c)
        return top_cases
