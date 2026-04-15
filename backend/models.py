from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(255), unique=True, nullable=False, index=True)
    type = Column(String(50), nullable=False)          # server | workstation | vm | switch | laptop
    ip_address = Column(String(45), nullable=False)
    os = Column(String(100))
    os_version = Column(String(100))
    last_patched = Column(DateTime, nullable=True)
    open_ports = Column(JSON, default=list, nullable=False)
    encryption_enabled = Column(Boolean, default=True, nullable=False)
    antivirus_active = Column(Boolean, default=True, nullable=False)
    password_policy_compliant = Column(Boolean, default=True, nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active | inactive
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    compliance_checks = relationship(
        "ComplianceCheck", back_populates="asset", cascade="all, delete-orphan"
    )


class ComplianceCheck(Base):
    __tablename__ = "compliance_checks"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    policy_name = Column(String(100), nullable=False)
    passed = Column(Boolean, nullable=False)
    severity = Column(String(20), nullable=False)  # CRITICAL | HIGH | MEDIUM | LOW
    detail = Column(Text)
    checked_at = Column(DateTime, server_default=func.now(), nullable=False)

    asset = relationship("Asset", back_populates="compliance_checks")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(100), nullable=False)
    detail = Column(Text)
    performed_at = Column(DateTime, server_default=func.now(), nullable=False)
