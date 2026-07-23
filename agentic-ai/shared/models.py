from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, JSON, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


# ── Credit & Compliance Policy RAG ─────────────────────────────────────────

class CreditPolicyChunk(Base):
    """RBI Master Directions, internal credit policy manual, and KYC/AML guideline chunks."""
    __tablename__ = "credit_policy_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    source_ref: Mapped[str] = mapped_column(String(200))    # e.g. "RBI/2022-23/Master Direction MSME, para 4.2"
    source_type: Mapped[str] = mapped_column(String(50))    # rbi_master_direction / internal_credit_policy / kyc_aml_guideline
    # embedding: Mapped[list] = mapped_column(Vector(1536))  # pgvector column, added via raw migration
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ── Enums ──────────────────────────────────────────────────────────────────

class CreditAppStatus(str, PyEnum):
    INTAKE = "intake"
    FINANCIAL_INGESTION = "financial_ingestion"
    BUREAU_TAX_VERIFICATION = "bureau_tax_verification"
    RISK_CASHFLOW_REVIEW = "risk_cashflow_review"
    CAM_DRAFTED = "cam_drafted"
    AWAITING_SIGNOFF = "awaiting_signoff"
    APPROVED = "approved"
    REJECTED = "rejected"


class FraudCaseStatus(str, PyEnum):
    SCORING = "scoring"
    AUTO_CLEARED = "auto_cleared"
    AUTO_FROZEN = "auto_frozen"
    ESCALATED = "escalated"
    ANALYST_CLEARED = "analyst_cleared"
    ANALYST_CONFIRMED_FRAUD = "analyst_confirmed_fraud"


class CollectionsStatus(str, PyEnum):
    SCORING = "scoring"
    OUTREACH_SENT = "outreach_sent"
    NEGOTIATING = "negotiating"
    SETTLED = "settled"
    PROMISE_TO_PAY = "promise_to_pay"
    ESCALATED = "escalated"
    UNRESOLVED = "unresolved"


# ── Audit Log ──────────────────────────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(100))
    before_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ── Use Case 1: MSME Credit CAM Prep ───────────────────────────────────────

class CreditApplication(Base):
    __tablename__ = "credit_applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    applicant_token: Mapped[str] = mapped_column(String(64))   # PAN/GSTIN tokenised
    loan_amount_requested: Mapped[float] = mapped_column(Float)
    business_vintage_years: Mapped[float] = mapped_column(Float)
    cibil_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gstr_filed_ok: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    cash_flow_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_flags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    recommended_pricing: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    cam_document_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[CreditAppStatus] = mapped_column(default=CreditAppStatus.INTAKE)
    credit_officer_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    signoff_decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    signoff_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ── Use Case 2: Fraud Detection & Investigation ────────────────────────────

class FraudCase(Base):
    __tablename__ = "fraud_cases"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    transaction_token: Mapped[str] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(20))            # card / upi / imps
    amount: Mapped[float] = mapped_column(Float)
    device_risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ip_reputation_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    velocity_anomaly: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    merchant_risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    aml_watchlist_hit: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    fraud_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommended_action: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # freeze/clear/escalate
    status: Mapped[FraudCaseStatus] = mapped_column(default=FraudCaseStatus.SCORING)
    analyst_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    final_decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    scored_in_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ── Use Case 3: Collections & Delinquency Recovery ─────────────────────────

class CollectionsAccount(Base):
    __tablename__ = "collections_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    customer_token: Mapped[str] = mapped_column(String(64))
    dpd_bucket: Mapped[str] = mapped_column(String(20))          # e.g. "1-30", "31-60"
    outstanding_amount: Mapped[float] = mapped_column(Float)
    payment_propensity_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    selected_channel: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # sms/whatsapp/voice
    settlement_offer: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    negotiation_outcome: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    escalation_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    escalation_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[CollectionsStatus] = mapped_column(default=CollectionsStatus.SCORING)
    collections_officer_token: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
