from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from a2_fraud_detection.coordinator import process_fraud_case
from shared.database import get_db
from shared.middleware import tokenise

router = APIRouter(prefix="/fraud", tags=["A2 — Fraud Detection & Investigation"])


class FraudCaseIn(BaseModel):
    transaction_id: str
    customer_id: str
    channel: str = Field(..., pattern="^(card|upi|imps)$")
    amount: float = Field(..., gt=0)
    device_id: str
    ip_address: str
    merchant_id: str
    beneficiary_id: str


class FraudCaseOut(BaseModel):
    case_id: str
    fraud_probability: float | None
    reasons: list[str]
    recommended_action: str | None
    scored_in_ms: int | None


class AnalystDecisionIn(BaseModel):
    analyst_id: str
    decision: str = Field(..., pattern="^(cleared|confirmed_fraud)$")
    notes: str = ""


@router.post("/score", response_model=FraudCaseOut)
async def score_transaction(body: FraudCaseIn, db: AsyncSession = Depends(get_db)):
    payload = {
        "transaction_token": tokenise(body.transaction_id),
        "customer_token": tokenise(body.customer_id),
        "channel": body.channel,
        "amount": body.amount,
        "device_id_token": tokenise(body.device_id),
        "ip_address": body.ip_address,
        "merchant_token": tokenise(body.merchant_id),
        "beneficiary_token": tokenise(body.beneficiary_id),
    }
    return await process_fraud_case(payload)


@router.get("/status/{case_id}")
async def get_fraud_case_status(case_id: str, db: AsyncSession = Depends(get_db)):
    from shared.models import FraudCase
    from sqlalchemy import select
    row = await db.execute(select(FraudCase).where(FraudCase.id == case_id))
    case = row.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Fraud case not found")
    return {"case_id": case.id, "status": case.status, "fraud_probability": case.fraud_probability}


@router.post("/analyst-decision/{case_id}")
async def analyst_decision(case_id: str, body: AnalystDecisionIn):
    """Level-2 analyst sign-off — only escalated cases (fraud_probability 0.3-0.7) reach this endpoint."""
    analyst_token = tokenise(body.analyst_id)
    return {"case_id": case_id, "decision": body.decision, "reviewed_by": analyst_token}
