"""
FastAPI router for Auto-Resolution Agent endpoints.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import AutoResolutionAudit
from services.auto_resolution_agent import auto_resolution_agent
from services.remediation_registry import ISSUE_TAXONOMY, REMEDIATION_REGISTRY

router = APIRouter(prefix="/api/auto-resolve", tags=["auto-resolution"])


# Request & Response Schemas
class EvaluateRequest(BaseModel):
    run_id: str
    record_id: str
    issue_type: str
    issue_description: str
    evidence: List[Dict[str, Any]] = []
    root_cause: Optional[str] = ""
    context_data: Optional[Dict[str, Any]] = {}


class ExecuteRequest(BaseModel):
    run_id: str
    record_id: str
    issue_id: str
    issue_type: str
    action_id: str
    executed_by: Optional[str] = "Operator (Verified)"
    context_data: Optional[Dict[str, Any]] = {}


@router.post("/evaluate")
def evaluate_issue_eligibility(req: EvaluateRequest):
    """
    Evaluate issue against the 10-point Decision Gate and evidence hierarchy.
    """
    result = auto_resolution_agent.evaluate_issue(
        run_id=req.run_id,
        record_id=req.record_id,
        issue_type=req.issue_type,
        issue_description=req.issue_description,
        evidence=req.evidence,
        root_cause=req.root_cause or "",
        context_data=req.context_data or {},
    )
    return result


@router.post("/execute")
def execute_remediation_action(req: ExecuteRequest, db: Session = Depends(get_db)):
    """
    Execute allowlisted remediation with snapshot, validation, rollback, and audit persistence.
    """
    result = auto_resolution_agent.execute_remediation(
        run_id=req.run_id,
        record_id=req.record_id,
        issue_id=req.issue_id,
        issue_type=req.issue_type,
        action_id=req.action_id,
        db=db,
        executed_by=req.executed_by or "Operator",
        context_data=req.context_data or {},
    )
    return result


@router.get("/history")
def get_resolution_history(
    run_id: Optional[str] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db)
):
    """
    Retrieve audit trail of all auto-remediations.
    """
    query = db.query(AutoResolutionAudit)
    if run_id:
        query = query.filter(AutoResolutionAudit.run_id == run_id)
    records = query.order_by(AutoResolutionAudit.created_at.desc()).limit(limit).all()
    return [r.to_dict() for r in records]


@router.get("/registry")
def get_remediation_registry():
    """
    Return controlled taxonomy and allowlisted remediation registry.
    """
    return {
        "taxonomy": ISSUE_TAXONOMY,
        "registry": REMEDIATION_REGISTRY,
    }
