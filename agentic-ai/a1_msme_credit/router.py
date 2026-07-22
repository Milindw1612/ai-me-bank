from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from a1_msme_credit.coordinator import process_credit_application
from shared.database import get_db
from shared.middleware import tokenise

router = APIRouter(prefix="/msme-credit", tags=["A1 — MSME Credit CAM Prep"])


class CreditApplicationIn(BaseModel):
    applicant_id: str = Field(..., description="Business PAN/GSTIN — tokenised before processing")
    loan_amount_requested: float = Field(..., gt=0)
    business_vintage_years: float = Field(..., ge=0)
    document_urls: list[str] = Field(default_factory=list, description="ITR/P&L/balance sheet uploads")


class CreditApplicationOut(BaseModel):
    application_id: str
    status: str
    recommended_pricing: str | None
    cam_document_ref: str | None
    risk_flags: list[str]


class SignoffIn(BaseModel):
    credit_officer_id: str
    decision: str = Field(..., pattern="^(approved|rejected)$")
    notes: str = ""


@router.post("/apply", response_model=CreditApplicationOut)
async def submit_application(body: CreditApplicationIn, db: AsyncSession = Depends(get_db)):
    payload = body.model_dump()
    payload["applicant_token"] = tokenise(payload.pop("applicant_id"))
    result = await process_credit_application(payload)
    return result


@router.get("/status/{application_id}")
async def get_application_status(application_id: str, db: AsyncSession = Depends(get_db)):
    from shared.models import CreditApplication
    from sqlalchemy import select
    row = await db.execute(select(CreditApplication).where(CreditApplication.id == application_id))
    app = row.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Credit application not found")
    return {
        "application_id": app.id,
        "status": app.status,
        "recommended_pricing": app.recommended_pricing,
        "cam_document_ref": app.cam_document_ref,
    }


@router.post("/signoff/{application_id}")
async def credit_officer_signoff(application_id: str, body: SignoffIn):
    """Final lending authority stays human — credit officer signs off on the drafted CAM."""
    officer_token = tokenise(body.credit_officer_id)
    return {
        "application_id": application_id,
        "decision": body.decision,
        "signed_off_by": officer_token,
    }
