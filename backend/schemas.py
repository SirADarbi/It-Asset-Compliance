from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime


# ── Asset ──────────────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    hostname: str
    type: str
    ip_address: str
    os: Optional[str] = None
    os_version: Optional[str] = None
    last_patched: Optional[datetime] = None
    open_ports: Optional[List[int]] = []
    encryption_enabled: bool = True
    antivirus_active: bool = True
    password_policy_compliant: bool = True
    status: str = "active"


class AssetUpdate(BaseModel):
    hostname: Optional[str] = None
    type: Optional[str] = None
    ip_address: Optional[str] = None
    os: Optional[str] = None
    os_version: Optional[str] = None
    last_patched: Optional[datetime] = None
    open_ports: Optional[List[int]] = None
    encryption_enabled: Optional[bool] = None
    antivirus_active: Optional[bool] = None
    password_policy_compliant: Optional[bool] = None
    status: Optional[str] = None


class AssetResponse(AssetCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


# ── ComplianceCheck ────────────────────────────────────────────────────────────

class ComplianceCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    policy_name: str
    passed: bool
    severity: str
    detail: Optional[str]
    checked_at: datetime
    asset: Optional[AssetResponse] = None


# ── AuditLog ───────────────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    detail: Optional[str]
    performed_at: datetime
