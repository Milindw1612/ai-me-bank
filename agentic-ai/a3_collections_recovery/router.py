from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from a3_collections_recovery.coordinator import process_collections_account
from shared.database import get_db
from shared.middleware import tokenise

router = APIRouter(prefix="/collections", tags=["A3 — Collections & Delinquency Recovery"])


class CollectionsAccountIn(BaseModel):
    customer_id: str
    dpd_bucket: str = Field(..., pattern="^(1-30|31-60|61-90)$")
    outstanding_amount: float = Field(..., gt=0)
    phone: str


class CollectionsAccountOut(BaseModel):
    account_id: str
    selected_channel: str | None
    settlement_offer: float | None
    negotiation_outcome: str | None
    escalation_flag: bool
    escalation_reason: str | None


class OfficerOutcomeIn(BaseModel):
    officer_id: str
    outcome: str = Field(..., pattern="^(settled|promise_to_pay|unresolved)$")
    notes: str = ""


@router.post("/process", response_model=CollectionsAccountOut)
async def process_account(body: CollectionsAccountIn, db: AsyncSession = Depends(get_db)):
    payload = {
        "customer_token": tokenise(body.customer_id),
        "dpd_bucket": body.dpd_bucket,
        "outstanding_amount": body.outstanding_amount,
        "phone_token": tokenise(body.phone),
    }
    return await process_collections_account(payload)


@router.get("/status/{account_id}")
async def get_account_status(account_id: str, db: AsyncSession = Depends(get_db)):
    from shared.models import CollectionsAccount
    from sqlalchemy import select
    row = await db.execute(select(CollectionsAccount).where(CollectionsAccount.id == account_id))
    acct = row.scalar_one_or_none()
    if not acct:
        raise HTTPException(status_code=404, detail="Collections account not found")
    return {"account_id": acct.id, "status": acct.status, "escalation_flag": acct.escalation_flag}


@router.post("/officer-outcome/{account_id}")
async def record_officer_outcome(account_id: str, body: OfficerOutcomeIn):
    """Human collections officer sign-off — only escalated/complex cases reach this endpoint."""
    officer_token = tokenise(body.officer_id)
    return {"account_id": account_id, "outcome": body.outcome, "recorded_by": officer_token}
