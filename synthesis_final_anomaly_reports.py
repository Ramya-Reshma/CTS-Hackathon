"""
Final Anomaly Report Synthesis Pipeline

Orchestrates Stage 7: Synthesizes comprehensive anomaly reports by:
  1. Loading flagged records from final_anomaly_report.json
  2. Grouping by severity tier (HIGH > 0.7, MEDIUM 0.4-0.7, LOW < 0.4)
  3. For each record, calling RCAAgent.run_rag_rca() with enriched evidence
  4. Validating output against RCAOutput schema
  5. Consolidating results to log/final_anomaly_synthesis_report.json

Batching Strategy: Hybrid Severity-First
  - Process HIGH severity records first, then MEDIUM, then LOW
  - Sequential processing (one record per RCA call for clarity and validation)
  - Exponential backoff retry on Bedrock API throttling
"""

import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
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
                        print(f"  ⚠ API throttled, retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries})")
                        time.sleep(delay)
                        continue
                raise
    
    def process_record(self, record: Dict[str, Any], severity_tier: str) -> Optional[Dict[str, Any]]:
        """Process a single anomaly record through RCA agent.
        
        Returns the synthesized report dict, or None if failed.
        """
        record_id = record.get("Record_ID") or record.get("record_id")
        
        try:
            # Step 1: Build evidence from record
            print(f"  Building evidence...", end=" ")
            evidence_pkg = build_evidence(record_id, report_path=str(self.anomaly_report_path))
            print("[OK]")
            
            # Step 2: Build RAG context from quality, correlation, statistical reports
            print(f"  Building RAG context...", end=" ")
            rag_context = build_synthesis_rag_context(
                record,
                self.quality_report,
                self.correlation_report,
                self.statistical_report,
            )
            print("[OK]")
            
            # Step 3: Retrieve similar historical cases for RAG
            print(f"  Retrieving historical cases...", end=" ")
            historical_cases = rag.retrieve_similar_cases(
                evidence_pkg,
                kb_path="log/historical_resolution_cases.json",
                limit=3
            )
            rag_context["historical_cases"] = historical_cases
            print(f"[OK] ({len(historical_cases)} cases)")
            
            # Step 4: Call RCA agent with RAG
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
            
            # Process record
            report = self.process_record(record, severity_tier=tier_name)
            
            if report:
                self.results.append(report)
                print(f"  Result: {report.get('severity', 'N/A')} severity, "
                      f"confidence={report.get('confidence', 0):.2f}")
            
            # Small delay to avoid API throttling
            if idx < len(records):
                time.sleep(0.5)
    
    def run(self, max_records_per_tier: Optional[int] = None) -> Dict[str, Any]:
        """Orchestrate the full synthesis pipeline.
        
        Args:
            max_records_per_tier: Limit records per tier for testing (None = all)
        
        Returns:
            Summary stats dict
        """
        print("\n" + "=" * 70)
        print("STAGE 7: FINAL ANOMALY REPORT SYNTHESIS PIPELINE")
        print("=" * 70)
        
        # Step 1: Load and group
        flagged_records = self.load_flagged_records()
        if not flagged_records:
            print("No flagged records to process. Exiting.")
            return self.stats
        
        print("\nGrouping by severity tier:")
        grouped = self.group_by_severity(flagged_records)
        
        # Optionally limit for testing
        if max_records_per_tier:
            for tier in grouped:
                grouped[tier] = grouped[tier][:max_records_per_tier]
            print(f"\n⚠ Limited to {max_records_per_tier} records per tier for testing")
        
        # Step 2: Process each tier in order (HIGH -> MEDIUM -> LOW)
        print("\n" + "=" * 70)
        print("PROCESSING BY SEVERITY TIER")
        print("=" * 70)
        
        for tier in ["HIGH", "MEDIUM", "LOW"]:
            self.process_tier(tier, grouped[tier])
        
        # Step 3: Save consolidated results
        print("\n" + "=" * 70)
        print("CONSOLIDATING RESULTS")
        print("=" * 70)
        
        output_data = {
            "synthesis_report": {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_records": self.stats["total_flagged"],
                "processed": self.stats["processed"],
                "succeeded": self.stats["succeeded"],
                "validation_failed": self.stats["validation_failed"],
                "api_failed": self.stats["api_failed"],
                "by_severity": self.stats["by_severity"],
            },
            "anomaly_reports": self.results,
        }
        
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"[OK] Saved {len(self.results)} synthesis reports to {self.output_path}")
        
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
    
    # Exit with error code if significant failures
    if stats["succeeded"] == 0:
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
