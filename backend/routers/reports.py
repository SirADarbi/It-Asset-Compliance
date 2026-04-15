from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import xml.etree.ElementTree as ET

import models
from database import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


def _get_latest_violations(db: Session):
    last_run = db.query(func.max(models.ComplianceCheck.checked_at)).scalar()
    if not last_run:
        return [], None
    violations = (
        db.query(models.ComplianceCheck)
        .filter(
            models.ComplianceCheck.checked_at == last_run,
            models.ComplianceCheck.passed == False,
        )
        .all()
    )
    return violations, last_run


@router.get("/json")
def report_json(db: Session = Depends(get_db)):
    """Return all failed checks from the latest run as JSON."""
    violations, last_run = _get_latest_violations(db)
    asset_map = {a.id: a for a in db.query(models.Asset).all()}

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "last_compliance_run": last_run.isoformat() if last_run else None,
        "total_violations": len(violations),
        "violations": [
            {
                "hostname": asset_map[v.asset_id].hostname if v.asset_id in asset_map else "unknown",
                "type": asset_map[v.asset_id].type if v.asset_id in asset_map else "",
                "ip_address": asset_map[v.asset_id].ip_address if v.asset_id in asset_map else "",
                "policy_name": v.policy_name,
                "severity": v.severity,
                "detail": v.detail,
                "checked_at": v.checked_at.isoformat(),
            }
            for v in sorted(violations, key=lambda x: (x.severity, x.policy_name))
        ],
    }


@router.get("/xml")
def report_xml(db: Session = Depends(get_db)):
    """Return all failed checks from the latest run as a downloadable XML file."""
    violations, last_run = _get_latest_violations(db)
    asset_map = {a.id: a for a in db.query(models.Asset).all()}

    root = ET.Element("ComplianceReport")
    ET.SubElement(root, "GeneratedAt").text = datetime.utcnow().isoformat()
    ET.SubElement(root, "LastComplianceRun").text = last_run.isoformat() if last_run else ""
    ET.SubElement(root, "TotalViolations").text = str(len(violations))

    violations_el = ET.SubElement(root, "Violations")
    for v in sorted(violations, key=lambda x: (x.severity, x.policy_name)):
        a = asset_map.get(v.asset_id)
        el = ET.SubElement(violations_el, "Violation")
        ET.SubElement(el, "Hostname").text = a.hostname if a else "unknown"
        ET.SubElement(el, "Type").text = a.type if a else ""
        ET.SubElement(el, "IPAddress").text = a.ip_address if a else ""
        ET.SubElement(el, "PolicyName").text = v.policy_name
        ET.SubElement(el, "Severity").text = v.severity
        ET.SubElement(el, "Detail").text = v.detail or ""
        ET.SubElement(el, "CheckedAt").text = v.checked_at.isoformat()

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": "attachment; filename=compliance_report.xml"},
    )
