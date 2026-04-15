"""
Integration tests for all API endpoints.

Uses a SQLite file database so no running Postgres instance is required.
DATABASE_URL is pointed at SQLite by conftest.py before any app module is
imported.  Each test gets a fully isolated schema via the clean_db fixture.

Run from backend/:  pytest tests/ -v
"""
import xml.etree.ElementTree as ET

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app  # triggers Base.metadata.create_all on the SQLite engine

# ── Test-scoped SQLite engine ─────────────────────────────────────────────────

_TEST_DB_URL = "sqlite:///./test_api.db"
_test_engine = create_engine(_TEST_DB_URL, connect_args={"check_same_thread": False})
_TestSession = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Wipe and recreate all tables before every test for full isolation."""
    Base.metadata.drop_all(bind=_test_engine)
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)


# ── Reusable payloads ─────────────────────────────────────────────────────────

_GOOD_ASSET = {
    "hostname": "web-server-01",
    "type": "server",
    "ip_address": "10.0.0.1",
    "open_ports": [443, 80],
    "encryption_enabled": True,
    "antivirus_active": True,
    "password_policy_compliant": True,
}

# Intentionally violates: telnet open (CRITICAL), RDP on workstation (HIGH),
# no encryption (CRITICAL), no antivirus (HIGH), bad password policy (MEDIUM),
# no last_patched (HIGH), SSH on workstation (MEDIUM).
_BAD_ASSET = {
    "hostname": "bad-workstation",
    "type": "workstation",
    "ip_address": "10.0.0.99",
    "open_ports": [22, 23, 3389],
    "encryption_enabled": False,
    "antivirus_active": False,
    "password_policy_compliant": False,
}


def _create_asset(payload: dict | None = None) -> dict:
    res = client.post("/assets/", json=payload or _GOOD_ASSET)
    assert res.status_code == 201, res.text
    return res.json()


# ══════════════════════════════════════════════════════════════════════════════
# Health
# ══════════════════════════════════════════════════════════════════════════════

def test_health_check():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert "version" in body


# ══════════════════════════════════════════════════════════════════════════════
# Assets — list
# ══════════════════════════════════════════════════════════════════════════════

def test_list_assets_empty_db():
    res = client.get("/assets/")
    assert res.status_code == 200
    assert res.json() == []


def test_list_assets_returns_created_asset():
    _create_asset()
    res = client.get("/assets/")
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["hostname"] == _GOOD_ASSET["hostname"]


def test_list_assets_pagination_skip_and_limit():
    for i in range(3):
        _create_asset({**_GOOD_ASSET, "hostname": f"host-{i}", "ip_address": f"10.0.0.{i}"})
    res = client.get("/assets/?skip=1&limit=1")
    assert res.status_code == 200
    assert len(res.json()) == 1


# ══════════════════════════════════════════════════════════════════════════════
# Assets — create
# ══════════════════════════════════════════════════════════════════════════════

def test_create_asset_returns_201():
    res = client.post("/assets/", json=_GOOD_ASSET)
    assert res.status_code == 201


def test_create_asset_response_contains_id_and_timestamp():
    body = _create_asset()
    assert isinstance(body["id"], int)
    assert "created_at" in body


def test_create_asset_all_fields_reflected():
    body = _create_asset()
    assert body["hostname"] == _GOOD_ASSET["hostname"]
    assert body["type"] == _GOOD_ASSET["type"]
    assert body["ip_address"] == _GOOD_ASSET["ip_address"]
    assert body["encryption_enabled"] is True


def test_create_asset_duplicate_hostname_returns_409():
    _create_asset()
    res = client.post("/assets/", json=_GOOD_ASSET)
    assert res.status_code == 409


def test_create_asset_missing_required_fields_returns_422():
    res = client.post("/assets/", json={"hostname": "only-hostname"})
    assert res.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# Assets — get by ID
# ══════════════════════════════════════════════════════════════════════════════

def test_get_asset_by_id_returns_correct_asset():
    created = _create_asset()
    res = client.get(f"/assets/{created['id']}")
    assert res.status_code == 200
    assert res.json()["hostname"] == _GOOD_ASSET["hostname"]


def test_get_asset_unknown_id_returns_404():
    res = client.get("/assets/9999")
    assert res.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Assets — update
# ══════════════════════════════════════════════════════════════════════════════

def test_update_asset_persists_new_field():
    created = _create_asset()
    res = client.put(f"/assets/{created['id']}", json={"os": "Ubuntu 22.04"})
    assert res.status_code == 200
    assert res.json()["os"] == "Ubuntu 22.04"


def test_update_asset_partial_patch_keeps_other_fields():
    created = _create_asset()
    res = client.put(f"/assets/{created['id']}", json={"os_version": "22.04.3"})
    assert res.status_code == 200
    body = res.json()
    assert body["os_version"] == "22.04.3"
    assert body["hostname"] == _GOOD_ASSET["hostname"]


def test_update_asset_unknown_id_returns_404():
    res = client.put("/assets/9999", json={"os": "Ubuntu"})
    assert res.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Assets — delete
# ══════════════════════════════════════════════════════════════════════════════

def test_delete_asset_returns_204():
    created = _create_asset()
    res = client.delete(f"/assets/{created['id']}")
    assert res.status_code == 204


def test_delete_asset_removes_it_from_list():
    created = _create_asset()
    client.delete(f"/assets/{created['id']}")
    res = client.get("/assets/")
    assert res.json() == []


def test_delete_asset_unknown_id_returns_404():
    res = client.delete("/assets/9999")
    assert res.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Compliance — before any run
# ══════════════════════════════════════════════════════════════════════════════

def test_compliance_results_empty_before_first_run():
    res = client.get("/compliance/results")
    assert res.status_code == 200
    assert res.json() == []


def test_compliance_summary_all_zeros_before_first_run():
    res = client.get("/compliance/summary")
    assert res.status_code == 200
    body = res.json()
    assert body["last_run"] is None
    assert body["total_violations"] == 0
    assert body["critical"] == 0


# ══════════════════════════════════════════════════════════════════════════════
# Compliance — run
# ══════════════════════════════════════════════════════════════════════════════

def test_compliance_run_returns_expected_summary_keys():
    _create_asset()
    res = client.post("/compliance/run")
    assert res.status_code == 200
    body = res.json()
    for key in ("assets_scanned", "total_checks", "failed"):
        assert key in body, f"missing key: {key}"


def test_compliance_run_bad_asset_produces_violations():
    _create_asset(_BAD_ASSET)
    client.post("/compliance/run")
    summary = client.get("/compliance/summary").json()
    assert summary["total_violations"] > 0


def test_compliance_run_good_asset_no_critical_violations():
    _create_asset(_GOOD_ASSET)
    client.post("/compliance/run")
    summary = client.get("/compliance/summary").json()
    assert summary["critical"] == 0


def test_compliance_results_filter_by_passed_false():
    _create_asset(_BAD_ASSET)
    client.post("/compliance/run")
    res = client.get("/compliance/results?passed=false")
    assert res.status_code == 200
    results = res.json()
    assert len(results) > 0
    assert all(not r["passed"] for r in results)


def test_compliance_results_filter_by_severity_critical():
    _create_asset(_BAD_ASSET)
    client.post("/compliance/run")
    res = client.get("/compliance/results?severity=CRITICAL")
    assert res.status_code == 200
    results = res.json()
    assert len(results) > 0
    assert all(r["severity"] == "CRITICAL" for r in results)


def test_compliance_summary_populated_after_run():
    _create_asset(_BAD_ASSET)
    client.post("/compliance/run")
    body = client.get("/compliance/summary").json()
    assert body["last_run"] is not None
    assert body["total_violations"] > 0


# ══════════════════════════════════════════════════════════════════════════════
# Reports
# ══════════════════════════════════════════════════════════════════════════════

def test_report_json_empty_before_run():
    res = client.get("/reports/json")
    assert res.status_code == 200
    body = res.json()
    assert body["total_violations"] == 0
    assert body["violations"] == []


def test_report_json_contains_violations_after_run():
    _create_asset(_BAD_ASSET)
    client.post("/compliance/run")
    body = client.get("/reports/json").json()
    assert body["total_violations"] > 0
    v = body["violations"][0]
    for field in ("hostname", "severity", "policy_name", "detail", "checked_at"):
        assert field in v, f"missing field in violation: {field}"


def test_report_xml_content_type_is_xml():
    res = client.get("/reports/xml")
    assert res.status_code == 200
    assert "xml" in res.headers["content-type"]


def test_report_xml_content_disposition_triggers_download():
    res = client.get("/reports/xml")
    cd = res.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "compliance_report.xml" in cd


def test_report_xml_is_parseable_with_correct_root():
    res = client.get("/reports/xml")
    root = ET.fromstring(res.content)
    assert root.tag == "ComplianceReport"
    assert root.find("TotalViolations") is not None
    assert root.find("Violations") is not None


def test_report_xml_violations_populated_after_run():
    _create_asset(_BAD_ASSET)
    client.post("/compliance/run")
    res = client.get("/reports/xml")
    root = ET.fromstring(res.content)
    violations = root.find("Violations")
    assert len(list(violations)) > 0
    first = list(violations)[0]
    assert first.find("Severity") is not None
    assert first.find("Hostname") is not None
