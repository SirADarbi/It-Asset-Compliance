"""
Pytest tests for every policy rule in engine/policy_checker.py.
No real database required — uses FakeAsset stub.
Run from backend/:  pytest tests/ -v
"""

from datetime import datetime, timedelta
import pytest

from engine.policy_checker import (
    check_patch_currency,
    check_telnet_port,
    check_encryption,
    check_antivirus,
    check_password_policy,
    check_rdp_exposure,
    check_ssh_on_workstation,
    POLICIES,
)


# ── FakeAsset stub ─────────────────────────────────────────────────────────────

class FakeAsset:
    def __init__(self, **kwargs):
        defaults = dict(
            type="server",
            last_patched=datetime.utcnow() - timedelta(days=5),
            open_ports=[],
            encryption_enabled=True,
            antivirus_active=True,
            password_policy_compliant=True,
            status="active",
        )
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


# ── 1. Patch currency ──────────────────────────────────────────────────────────

def test_patch_current_passes():
    asset = FakeAsset(last_patched=datetime.utcnow() - timedelta(days=10))
    r = check_patch_currency(asset)
    assert r["passed"] is True

def test_patch_40_days_is_high():
    asset = FakeAsset(last_patched=datetime.utcnow() - timedelta(days=40))
    r = check_patch_currency(asset)
    assert r["passed"] is False
    assert r["severity"] == "HIGH"

def test_patch_65_days_is_critical():
    asset = FakeAsset(last_patched=datetime.utcnow() - timedelta(days=65))
    r = check_patch_currency(asset)
    assert r["passed"] is False
    assert r["severity"] == "CRITICAL"

def test_no_patch_date_is_high():
    asset = FakeAsset(last_patched=None)
    r = check_patch_currency(asset)
    assert r["passed"] is False
    assert r["severity"] == "HIGH"

def test_patch_exactly_30_days_passes():
    asset = FakeAsset(last_patched=datetime.utcnow() - timedelta(days=30))
    r = check_patch_currency(asset)
    assert r["passed"] is True

def test_patch_exactly_61_days_is_critical():
    asset = FakeAsset(last_patched=datetime.utcnow() - timedelta(days=61))
    r = check_patch_currency(asset)
    assert r["severity"] == "CRITICAL"


# ── 2. Telnet port ─────────────────────────────────────────────────────────────

def test_telnet_open_is_critical():
    asset = FakeAsset(open_ports=[23])
    r = check_telnet_port(asset)
    assert r["passed"] is False
    assert r["severity"] == "CRITICAL"

def test_no_telnet_passes():
    asset = FakeAsset(open_ports=[80, 443])
    r = check_telnet_port(asset)
    assert r["passed"] is True

def test_telnet_among_other_ports_fails():
    asset = FakeAsset(open_ports=[80, 23, 443])
    r = check_telnet_port(asset)
    assert r["passed"] is False

def test_no_ports_passes_telnet():
    asset = FakeAsset(open_ports=[])
    r = check_telnet_port(asset)
    assert r["passed"] is True

def test_none_ports_passes_telnet():
    asset = FakeAsset(open_ports=None)
    r = check_telnet_port(asset)
    assert r["passed"] is True


# ── 3. Encryption ──────────────────────────────────────────────────────────────

def test_encryption_disabled_is_critical():
    asset = FakeAsset(encryption_enabled=False)
    r = check_encryption(asset)
    assert r["passed"] is False
    assert r["severity"] == "CRITICAL"

def test_encryption_enabled_passes():
    asset = FakeAsset(encryption_enabled=True)
    r = check_encryption(asset)
    assert r["passed"] is True


# ── 4. Antivirus ───────────────────────────────────────────────────────────────

def test_antivirus_inactive_is_high():
    asset = FakeAsset(antivirus_active=False)
    r = check_antivirus(asset)
    assert r["passed"] is False
    assert r["severity"] == "HIGH"

def test_antivirus_active_passes():
    asset = FakeAsset(antivirus_active=True)
    r = check_antivirus(asset)
    assert r["passed"] is True


# ── 5. Password policy ─────────────────────────────────────────────────────────

def test_password_non_compliant_is_medium():
    asset = FakeAsset(password_policy_compliant=False)
    r = check_password_policy(asset)
    assert r["passed"] is False
    assert r["severity"] == "MEDIUM"

def test_password_compliant_passes():
    asset = FakeAsset(password_policy_compliant=True)
    r = check_password_policy(asset)
    assert r["passed"] is True


# ── 6. RDP exposure ────────────────────────────────────────────────────────────

def test_rdp_on_workstation_is_high():
    asset = FakeAsset(type="workstation", open_ports=[3389])
    r = check_rdp_exposure(asset)
    assert r["passed"] is False
    assert r["severity"] == "HIGH"

def test_rdp_on_server_passes():
    asset = FakeAsset(type="server", open_ports=[3389])
    r = check_rdp_exposure(asset)
    assert r["passed"] is True

def test_rdp_on_laptop_is_high():
    asset = FakeAsset(type="laptop", open_ports=[3389])
    r = check_rdp_exposure(asset)
    assert r["passed"] is False
    assert r["severity"] == "HIGH"

def test_no_rdp_on_workstation_passes():
    asset = FakeAsset(type="workstation", open_ports=[80])
    r = check_rdp_exposure(asset)
    assert r["passed"] is True


# ── 7. SSH on workstation ──────────────────────────────────────────────────────

def test_ssh_on_workstation_is_medium():
    asset = FakeAsset(type="workstation", open_ports=[22])
    r = check_ssh_on_workstation(asset)
    assert r["passed"] is False
    assert r["severity"] == "MEDIUM"

def test_ssh_on_server_passes():
    asset = FakeAsset(type="server", open_ports=[22])
    r = check_ssh_on_workstation(asset)
    assert r["passed"] is True

def test_ssh_on_vm_passes():
    asset = FakeAsset(type="vm", open_ports=[22])
    r = check_ssh_on_workstation(asset)
    assert r["passed"] is True

def test_no_ssh_on_workstation_passes():
    asset = FakeAsset(type="workstation", open_ports=[443])
    r = check_ssh_on_workstation(asset)
    assert r["passed"] is True


# ── 8. POLICIES registry ───────────────────────────────────────────────────────

def test_policies_registry_has_seven_rules():
    assert len(POLICIES) == 7

def test_all_results_have_required_keys():
    asset = FakeAsset()
    for fn in POLICIES:
        r = fn(asset)
        assert "policy_name" in r
        assert "passed" in r
        assert "severity" in r
        assert "detail" in r

def test_clean_asset_passes_all_rules():
    asset = FakeAsset()
    results = [fn(asset) for fn in POLICIES]
    assert all(r["passed"] for r in results)

def test_worst_case_asset_fails_all_rules():
    asset = FakeAsset(
        type="workstation",
        last_patched=datetime.utcnow() - timedelta(days=200),
        open_ports=[22, 23, 3389],
        encryption_enabled=False,
        antivirus_active=False,
        password_policy_compliant=False,
    )
    results = [fn(asset) for fn in POLICIES]
    assert all(not r["passed"] for r in results)
