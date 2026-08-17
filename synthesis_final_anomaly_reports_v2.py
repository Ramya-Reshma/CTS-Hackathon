"""
Updated Final Anomaly Report Synthesis Pipeline

Orchestrates Stage 7 with reformatted output including:
- Priority (1-Critical, 2-High, 3-Medium, 4-Low)
- Record ID
- Type (record type)
- Anomaly (classification)
- Severity
- Primary Signal
- Likely Root Cause
- Recommended Action
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

# Project imports
from UC10_Anomaly_Monitor.rca.agent import RCAAgent
from UC10_Anomaly_Monitor.rca.evidence_builder import build_evidence
from UC10_Anomaly_Monitor.rca import rag
from synthesis_rag_context_builder import (
    load_quality_report,
    load_correlation_findings,
    load_statistical_findings,
    build_synthesis_rag_context,
    format_rag_context_for_prompt,
)


class AnomalyClassifier:
    """Classify anomalies by type based on evidence and root cause."""
    
    ANOMALY_TYPES = {
        "Provider": ["provider", "npi", "practitioner", "specialty", "credentialing", "panel"],
        "Financial": ["amount", "billed", "paid", "allowed", "zero-pay", "reimburse", "cost"],
        "Timing": ["date", "submission", "processing", "service_date", "delay"],
        "Quantity": ["quantity", "days_supply", "dose", "volume", "dispense"],
        "Relationship": ["correlation", "residual", "relationship", "pattern"],
        "Quality": ["missing", "invalid", "format", "completeness", "validity", "consistency"],
        "Frequency": ["high", "low", "outlier", "anomalous", "deviation", "zscore"],
        "Authorization": ["auth", "approval", "authorization", "denial", "reject"],
    }
    
    @classmethod
    def classify(cls, record: Dict[str, Any]) -> str:
        """Classify anomaly type based on available evidence."""
        if "rag_context" in record and record["rag_context"].get("historical_cases"):
            for case in record["rag_context"]["historical_cases"]:
                anomaly_name = case.get("anomaly_name") or case.get("anomaly") or ""
                if anomaly_name:
                    for anomaly_type, keywords in cls.ANOMALY_TYPES.items():
                        if any(kw in anomaly_name.lower() for kw in keywords):
                            return anomaly_type
        
        root_cause = (record.get("likely_root_cause") or "").lower()
        for anomaly_type, keywords in cls.ANOMALY_TYPES.items():
            if any(kw in root_cause for kw in keywords):
                return anomaly_type
        
        return "Frequency" if record.get("rag_context", {}).get("ml_signal_count", 0) > 1 else "Other"
    
    @classmethod
    def extract_primary_signal(cls, record: Dict[str, Any]) -> str:
        """Extract the primary anomaly signal."""
        if "rag_context" in record and record["rag_context"].get("historical_cases"):
            for case in record["rag_context"]["historical_cases"]:
                anomaly_name = case.get("anomaly_name") or case.get("anomaly") or ""
                if anomaly_name:
                    return anomaly_name
        
        signals = record.get("anomaly_signals") or {}
        if signals:
            for signal_name in signals.keys():
                return signal_name
        
        if record.get("observed_facts"):
            return record["observed_facts"][0]
        
        return f"{record.get('record_type')} anomaly detected"


def severity_to_priority(severity: str) -> str:
    """Convert severity to priority level."""
    severity_lower = (severity or "").lower()
    if severity_lower in ["high", "critical", "severe"]:
        return "1-Critical"
    elif severity_lower == "medium":
        return "2-High"
    elif severity_lower == "low":
        return "3-Medium"
    else:
        return "4-Low"


def extract_first_recommended_action(record: Dict[str, Any]) -> str:
    """Extract the first recommended action."""
    actions = record.get("recommended_actions") or []
    if actions:
        return actions[0]
    
    if "rag_context" in record and record["rag_context"].get("historical_cases"):
        for case in record["rag_context"]["historical_cases"]:
            case_actions = case.get("recommended_actions") or []
            if case_actions:
                return case_actions[0]
    
    return "Review evidence and implement corrective action"


class SynthesisOrchestrator:
    def __init__(self):
        self.anomaly_report_path = Path("log/final_anomaly_report.json")
        self.quality_report_path = Path("log/quality_report.json")
        self.correlation_report_path = Path("log/correlation_findings.json")
        self.statistical_report_path = Path("log/statistical_findings.json")
        self.output_path = Path("log/final_anomaly_synthesis_report.json")
        
        self.quality_report = load_quality_report(str(self.quality_report_path))
        self.correlation_report = load_correlation_findings(str(self.correlation_report_path))
        self.statistical_report = load_statistical_findings(str(self.statistical_report_path))
        
        self.agent = RCAAgent()
        
        # Tracking
        self.results = []
        self.stats = {
            "total_flagged": 0,
            "processed": 0,
            "succeeded": 0,
            "validation_failed": 0,
            "api_failed": 0,
            "by_severity": {},
        }
    
    def _map_severity_tier(self, severity_score: float) -> str:
        """Map ISO_Severity_0to1 score to HIGH/MEDIUM/LOW tier."""
        if severity_score is None:
            return "LOW"
        try:
            score = float(severity_score)
            if score > 0.7:
                return "HIGH"
            elif score >= 0.4:
                return "MEDIUM"
            else:
                return "LOW"
        except (ValueError, TypeError):
            return "LOW"
    
    def load_flagged_records(self) -> List[Dict[str, Any]]:
        """Load and filter for ML_Is_Anomalous = True records."""
        print(f"Loading anomaly report from {self.anomaly_report_path}...")
        
        if not self.anomaly_report_path.exists():
            print(f"ERROR: {self.anomaly_report_path} not found")
            return []
        
        with open(self.anomaly_report_path, "r", encoding="utf-8") as f:
            all_records = json.load(f)
        
        flagged = [r for r in all_records if r.get("ML_Is_Anomalous", False)]
        print(f"[OK] Loaded {len(all_records)} total records, {len(flagged)} flagged as anomalous")
        
        self.stats["total_flagged"] = len(flagged)
        return flagged
    
    def group_by_severity(self, records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group records into severity tiers."""
        grouped = {"HIGH": [], "MEDIUM": [], "LOW": []}
        
        for record in records:
            score = record.get("ISO_Severity_0to1") or 0.0
            tier = self._map_severity_tier(score)
            grouped[tier].append(record)
        
        for tier in ["HIGH", "MEDIUM", "LOW"]:
            count = len(grouped[tier])
            self.stats["by_severity"][tier] = count
            print(f"  {tier:8s}: {count:4d} records")
        
        return grouped
    
    def _retry_with_backoff(self, func, max_retries: int = 3, base_delay: float = 2.0):
        """Retry a function with exponential backoff for API throttling."""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if "ThrottlingException" in str(e) or "rate" in str(e).lower():
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"  [WARNING] API throttled, retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                        continue
                raise
    
    def process_record(self, record: Dict[str, Any], severity_tier: str) -> Optional[Dict[str, Any]]:
        """Process a single anomaly record through RCA agent."""
        record_id = record.get("Record_ID") or record.get("record_id")
        
        try:
            print(f"  Building evidence...", end=" ")
            evidence_pkg = build_evidence(record_id, report_path=str(self.anomaly_report_path))
            print("[OK]")
            
            print(f"  Building RAG context...", end=" ")
            rag_context = build_synthesis_rag_context(
                record,
                self.quality_report,
                self.correlation_report,
                self.statistical_report,
            )
            print("[OK]")
            
            print(f"  Retrieving historical cases...", end=" ")
            historical_cases = rag.retrieve_similar_cases(
                evidence_pkg,
                kb_path="log/historical_resolution_cases.json",
                limit=3
            )
            rag_context["historical_cases"] = historical_cases
            print(f"[OK] ({len(historical_cases)} cases)")
            
            print(f"  Calling RCA agent...", end=" ")
            
            def run_rca():
                return self.agent.run_rag_rca(
                    evidence_package=evidence_pkg,
                    historical_cases=historical_cases,
                    kb_path="log/historical_resolution_cases.json"
                )
            
            rca_output = self._retry_with_backoff(run_rca)
            print("[OK]")
            
            # Convert RCAOutput Pydantic model to dict
            report_dict = rca_output.model_dump()
            
            # Enrich with synthesis metadata
            report_dict["synthesis_metadata"] = {
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "severity_tier": severity_tier,
                "rag_context_applied": True,
                "validation_status": "passed",
            }
            
            # Store RAG context as reference
            report_dict["rag_context"] = rag_context
            
            self.stats["succeeded"] += 1
            return report_dict
        
        except json.JSONDecodeError as e:
            print(f"[FAIL] JSON parsing error: {e}")
            self.stats["validation_failed"] += 1
            return None
        except ValueError as e:
            if "RCA" in str(e) or "validation" in str(e).lower():
                print(f"[FAIL] Schema validation error: {e}")
                self.stats["validation_failed"] += 1
            else:
                print(f"[FAIL] Error: {e}")
                self.stats["api_failed"] += 1
            return None
        except Exception as e:
            print(f"[FAIL] Unexpected error: {e}")
            self.stats["api_failed"] += 1
            return None
    
    def process_tier(self, tier_name: str, records: List[Dict[str, Any]]) -> None:
        """Process all records in a severity tier."""
        if not records:
            print(f"\n{tier_name} tier: 0 records (skipping)")
            return
        
        print(f"\n{tier_name} tier: {len(records)} records")
        print("=" * 70)
        
        for idx, record in enumerate(records, 1):
            record_id = record.get("Record_ID") or record.get("record_id")
            progress = f"[{idx}/{len(records)}]"
            print(f"\n{progress} Processing {record_id}...")
            
            self.stats["processed"] += 1
            
            report = self.process_record(record, severity_tier=tier_name)
            
            if report:
                self.results.append(report)
                print(f"  Result: {report.get('severity', 'N/A')} severity, confidence={report.get('confidence', 0):.2f}")
            
            if idx < len(records):
                time.sleep(0.5)
    
    def reformat_report(self, raw_reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Reformat raw RCA reports to the requested format."""
        reformatted = []
        
        for idx, record in enumerate(raw_reports, 1):
            reformatted_record = {
                "Priority": severity_to_priority(record.get("severity")),
                "Record ID": record.get("incident_id") or record.get("record_id") or f"REC-{idx}",
                "Type": record.get("record_type") or "CLAIM",
                "Anomaly": AnomalyClassifier.classify(record),
                "Severity": record.get("severity") or "MEDIUM",
                "Primary Signal": AnomalyClassifier.extract_primary_signal(record),
                "Likely Root Cause": record.get("likely_root_cause") or "Unknown",
                "Recommended Action": extract_first_recommended_action(record),
                "_metadata": {
                    "confidence": record.get("confidence", 0.0),
                    "impact": record.get("impact") or "Not specified",
                    "additional_checks": record.get("additional_checks_required", []),
                    "processed_at": record.get("synthesis_metadata", {}).get("processed_at"),
                }
            }
            reformatted.append(reformatted_record)
        
        # Sort by priority
        reformatted.sort(key=lambda x: (x["Priority"], x["Record ID"]))
        return reformatted
    
    def run(self, max_records_per_tier: Optional[int] = None) -> Dict[str, Any]:
        """Orchestrate the full synthesis pipeline."""
        print("\n" + "=" * 70)
        print("STAGE 7: FINAL ANOMALY REPORT SYNTHESIS PIPELINE")
        print("=" * 70)
        
        flagged_records = self.load_flagged_records()
        if not flagged_records:
            print("No flagged records to process. Exiting.")
            return self.stats
        
        print("\nGrouping by severity tier:")
        grouped = self.group_by_severity(flagged_records)
        
        if max_records_per_tier:
            for tier in grouped:
                grouped[tier] = grouped[tier][:max_records_per_tier]
            print(f"\n[WARNING] Limited to {max_records_per_tier} records per tier for testing")
        
        print("\n" + "=" * 70)
        print("PROCESSING BY SEVERITY TIER")
        print("=" * 70)
        
        for tier in ["HIGH", "MEDIUM", "LOW"]:
            self.process_tier(tier, grouped[tier])
        
        print("\n" + "=" * 70)
        print("REFORMATTING RESULTS")
        print("=" * 70)
        
        # Reformat to requested structure
        reformatted_reports = self.reformat_report(self.results)
        
        output_data = {
            "report_metadata": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_anomalies": len(reformatted_reports),
                "by_severity": self.stats["by_severity"],
                "format": "Priority | Record ID | Type | Anomaly | Severity | Primary Signal | Likely Root Cause | Recommended Action",
            },
            "anomalies": reformatted_reports,
        }
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Saved {len(reformatted_reports)} synthesis reports to {self.output_path}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("SYNTHESIS PIPELINE SUMMARY")
        print("=" * 70)
        print(f"Total flagged anomalies:        {self.stats['total_flagged']}")
        print(f"Records processed:              {self.stats['processed']}")
        print(f"Successfully synthesized:       {self.stats['succeeded']}")
        print(f"Schema validation failures:     {self.stats['validation_failed']}")
        print(f"API/processing failures:        {self.stats['api_failed']}")
        print(f"\nBy severity tier:")
        for tier in ["HIGH", "MEDIUM", "LOW"]:
            print(f"  {tier:8s}: {self.stats['by_severity'].get(tier, 0)}")
        
        if self.stats["succeeded"] > 0:
            success_rate = (self.stats["succeeded"] / self.stats["processed"]) * 100
            print(f"\nSuccess rate: {success_rate:.1f}%")
        
        print("=" * 70)
        
        return self.stats


def main():
    """Entry point for synthesis pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Synthesize final anomaly reports with RAG + RCA")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit records per severity tier (for testing)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="log/final_anomaly_synthesis_report.json",
        help="Output file path",
    )
    
    args = parser.parse_args()
    
    orchestrator = SynthesisOrchestrator()
    if args.output:
        orchestrator.output_path = Path(args.output)
    
    stats = orchestrator.run(max_records_per_tier=args.limit)
    
    if stats["succeeded"] == 0:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
