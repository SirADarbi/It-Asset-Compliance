"""
Seed the database with 7 realistic assets covering varied compliance states.
Run from backend/:  python3 seed.py
"""

from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)

NOW = datetime.utcnow()

ASSETS = [
    # 1. Fully compliant server
    {
        "hostname": "core-web-01",
        "type": "server",
        "ip_address": "10.0.1.10",
        "os": "Ubuntu",
        "os_version": "22.04 LTS",
        "last_patched": NOW - timedelta(days=5),
        "open_ports": [80, 443],
        "encryption_enabled": True,
        "antivirus_active": True,
        "password_policy_compliant": True,
        "status": "active",
    },
    # 2. Server with Telnet open (CRITICAL)
    {
        "hostname": "legacy-db-01",
        "type": "server",
        "ip_address": "10.0.1.20",
        "os": "CentOS",
        "os_version": "7",
        "last_patched": NOW - timedelta(days=20),
        "open_ports": [3306, 23],
        "encryption_enabled": True,
        "antivirus_active": True,
        "password_policy_compliant": True,
        "status": "active",
    },
    # 3. Workstation with no encryption (CRITICAL)
    {
        "hostname": "workstation-finance-01",
        "type": "workstation",
        "ip_address": "10.0.2.50",
        "os": "Windows",
        "os_version": "10 Pro",
        "last_patched": NOW - timedelta(days=15),
        "open_ports": [80],
        "encryption_enabled": False,
        "antivirus_active": True,
        "password_policy_compliant": True,
        "status": "active",
    },
    # 4. Workstation with RDP open (HIGH)
    {
        "hostname": "workstation-dev-01",
        "type": "workstation",
        "ip_address": "10.0.2.60",
        "os": "Windows",
        "os_version": "11 Pro",
        "last_patched": NOW - timedelta(days=25),
        "open_ports": [3389, 8080],
        "encryption_enabled": True,
        "antivirus_active": True,
        "password_policy_compliant": True,
        "status": "active",
    },
    # 5. Switch — 90 days unpatched + Telnet open (CRITICAL x2)
    {
        "hostname": "core-switch-01",
        "type": "switch",
        "ip_address": "10.0.0.1",
        "os": "Cisco IOS",
        "os_version": "15.2",
        "last_patched": NOW - timedelta(days=90),
        "open_ports": [23, 22, 80],
        "encryption_enabled": True,
        "antivirus_active": True,
        "password_policy_compliant": True,
        "status": "active",
    },
    # 6. VM — fully compliant
    {
        "hostname": "vm-prod-01",
        "type": "vm",
        "ip_address": "10.0.3.10",
        "os": "Ubuntu",
        "os_version": "20.04 LTS",
        "last_patched": NOW - timedelta(days=10),
        "open_ports": [443],
        "encryption_enabled": True,
        "antivirus_active": True,
        "password_policy_compliant": True,
        "status": "active",
    },
    # 7. Workstation with no antivirus (HIGH)
    {
        "hostname": "workstation-hr-01",
        "type": "workstation",
        "ip_address": "10.0.2.70",
        "os": "Windows",
        "os_version": "10 Home",
        "last_patched": NOW - timedelta(days=12),
        "open_ports": [80],
        "encryption_enabled": True,
        "antivirus_active": False,
        "password_policy_compliant": True,
        "status": "active",
    },
]


def seed():
    db = SessionLocal()
    try:
        existing = db.query(models.Asset).count()
        if existing:
            print(f"Found {existing} existing asset(s). Clearing and re-seeding...")
            db.query(models.ComplianceCheck).delete()
            db.query(models.AuditLog).delete()
            db.query(models.Asset).delete()
            db.commit()

        for data in ASSETS:
            db.add(models.Asset(**data))
        db.commit()
        print(f"Seeded {len(ASSETS)} assets.")

        db.add(models.AuditLog(
            action="database_seeded",
            detail=f"Inserted {len(ASSETS)} assets via seed.py",
        ))
        db.commit()
        print("Audit log entry created.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
