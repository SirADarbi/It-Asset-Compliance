from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

import models
import schemas
from database import get_db
from engine.policy_checker import run_compliance_checks

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.post("/run")
def run_compliance(db: Session = Depends(get_db)):
    """Execute all policy rules against every active asset and persist results."""
    return run_compliance_checks(db)


@router.get("/results", response_model=List[schemas.ComplianceCheckResponse])
def get_results(
    passed: Optional[bool] = Query(None, description="Filter by passed status"),
    severity: Optional[str] = Query(None, description="Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"),
    db: Session = Depends(get_db),
):
    """Return compliance check results from the latest run, optionally filtered."""
    last_run = db.query(func.max(models.ComplianceCheck.checked_at)).scalar()
    if not last_run:
        return []

    query = db.query(models.ComplianceCheck).filter(
        models.ComplianceCheck.checked_at == last_run
    )
    if passed is not None:
        query = query.filter(models.ComplianceCheck.passed == passed)
    if severity:
        query = query.filter(models.ComplianceCheck.severity == severity.upper())

    return query.order_by(
        models.ComplianceCheck.severity,
        models.ComplianceCheck.checked_at.desc()
    ).all()


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    """Return violation counts by severity plus the last run timestamp."""
    last_run = db.query(func.max(models.ComplianceCheck.checked_at)).scalar()
    if not last_run:
        return {"last_run": None, "critical": 0, "high": 0, "medium": 0, "low": 0, "total_violations": 0}

    violations = (
        db.query(models.ComplianceCheck)
        .filter(
            models.ComplianceCheck.checked_at == last_run,
            models.ComplianceCheck.passed == False,
        )
        .all()
    )

    return {
        "last_run": last_run.isoformat(),
        "critical": sum(1 for v in violations if v.severity == "CRITICAL"),
        "high": sum(1 for v in violations if v.severity == "HIGH"),
        "medium": sum(1 for v in violations if v.severity == "MEDIUM"),
        "low": sum(1 for v in violations if v.severity == "LOW"),
        "total_violations": len(violations),
    }
