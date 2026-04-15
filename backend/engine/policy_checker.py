"""
Compliance policy engine.

Each rule function accepts an Asset-like object and returns:
  {
      "policy_name": str,
      "passed":      bool,
      "severity":    "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
      "detail":      str,
  }

run_compliance_checks(db) orchestrates all rules against every active asset,
persists results to compliance_checks and audit_log, and returns a summary dict.
"""

from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session


# ── Individual policy rules ────────────────────────────────────────────────────

def check_patch_currency(asset) -> Dict:
    if asset.last_patched is None:
        return {
            "policy_name": "patch_currency",
            "passed": False,
            "severity": "HIGH",
            "detail": "No patch date recorded — patch status unknown.",
        }
    days = (datetime.utcnow() - asset.last_patched).days
    if days > 60:
        return {
            "policy_name": "patch_currency",
            "passed": False,
            "severity": "CRITICAL",
            "detail": f"Last patched {days} days ago (>60 days threshold).",
        }
    if days > 30:
        return {
            "policy_name": "patch_currency",
            "passed": False,
            "severity": "HIGH",
            "detail": f"Last patched {days} days ago (>30 days threshold).",
        }
    return {
        "policy_name": "patch_currency",
        "passed": True,
        "severity": "LOW",
        "detail": f"Last patched {days} days ago — within acceptable window.",
    }


def check_telnet_port(asset) -> Dict:
    ports = asset.open_ports or []
    if 23 in ports:
        return {
            "policy_name": "telnet_port",
            "passed": False,
            "severity": "CRITICAL",
            "detail": "Telnet (port 23) is open. Plaintext protocol — disable immediately.",
        }
    return {
        "policy_name": "telnet_port",
        "passed": True,
        "severity": "LOW",
        "detail": "Telnet port (23) is not open.",
    }


def check_encryption(asset) -> Dict:
    if not asset.encryption_enabled:
        return {
            "policy_name": "encryption",
            "passed": False,
            "severity": "CRITICAL",
            "detail": "Disk encryption is disabled. Data at rest is unprotected.",
        }
    return {
        "policy_name": "encryption",
        "passed": True,
        "severity": "LOW",
        "detail": "Disk encryption is enabled.",
    }


def check_antivirus(asset) -> Dict:
    if not asset.antivirus_active:
        return {
            "policy_name": "antivirus",
            "passed": False,
            "severity": "HIGH",
            "detail": "Antivirus is not active. Asset is unprotected against malware.",
        }
    return {
        "policy_name": "antivirus",
        "passed": True,
        "severity": "LOW",
        "detail": "Antivirus is active.",
    }


def check_password_policy(asset) -> Dict:
    if not asset.password_policy_compliant:
        return {
            "policy_name": "password_policy",
            "passed": False,
            "severity": "MEDIUM",
            "detail": "Password policy requirements not met (complexity/length/rotation).",
        }
    return {
        "policy_name": "password_policy",
        "passed": True,
        "severity": "LOW",
        "detail": "Password policy is compliant.",
    }


def check_rdp_exposure(asset) -> Dict:
    ports = asset.open_ports or []
    if asset.type in ("workstation", "laptop") and 3389 in ports:
        return {
            "policy_name": "rdp_exposure",
            "passed": False,
            "severity": "HIGH",
            "detail": "RDP (port 3389) is open on a workstation — unauthorized remote access risk.",
        }
    return {
        "policy_name": "rdp_exposure",
        "passed": True,
        "severity": "LOW",
        "detail": "RDP exposure check passed.",
    }


def check_ssh_on_workstation(asset) -> Dict:
    ports = asset.open_ports or []
    if asset.type in ("workstation", "laptop") and 22 in ports:
        return {
            "policy_name": "ssh_on_workstation",
            "passed": False,
            "severity": "MEDIUM",
            "detail": "SSH (port 22) is open on a workstation — workstations should not expose SSH.",
        }
    return {
        "policy_name": "ssh_on_workstation",
        "passed": True,
        "severity": "LOW",
        "detail": "SSH on workstation check passed.",
    }


# ── Policy registry ────────────────────────────────────────────────────────────

POLICIES = [
    check_patch_currency,
    check_telnet_port,
    check_encryption,
    check_antivirus,
    check_password_policy,
    check_rdp_exposure,
    check_ssh_on_workstation,
]


# ── Orchestrator ───────────────────────────────────────────────────────────────

def run_compliance_checks(db: Session) -> Dict:
    """
    Run all policy rules against every active asset.
    Clears previous results, writes new ComplianceCheck rows and an AuditLog entry.
    Returns a summary dict.
    """
    from models import Asset, ComplianceCheck, AuditLog

    assets = db.query(Asset).filter(Asset.status == "active").all()

    # Clear previous results for a clean slate
    db.query(ComplianceCheck).delete()
    db.flush()

    now = datetime.utcnow()
    counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    total = passed = 0

    for asset in assets:
        for policy_fn in POLICIES:
            result = policy_fn(asset)
            check = ComplianceCheck(
                asset_id=asset.id,
                policy_name=result["policy_name"],
                passed=result["passed"],
                severity=result["severity"],
                detail=result["detail"],
                checked_at=now,
            )
            db.add(check)
            total += 1
            if result["passed"]:
                passed += 1
            else:
                counts[result["severity"]] += 1

    failed = total - passed

    log = AuditLog(
        action="compliance_run",
        detail=(
            f"Scanned {len(assets)} assets, {total} checks. "
            f"Failed: {failed} "
            f"(CRITICAL={counts['CRITICAL']}, HIGH={counts['HIGH']}, "
            f"MEDIUM={counts['MEDIUM']}, LOW={counts['LOW']})"
        ),
        performed_at=now,
    )
    db.add(log)
    db.commit()

    return {
        "assets_scanned": len(assets),
        "total_checks": total,
        "passed": passed,
        "failed": failed,
        "critical": counts["CRITICAL"],
        "high": counts["HIGH"],
        "medium": counts["MEDIUM"],
        "low": counts["LOW"],
        "timestamp": now.isoformat(),
    }
