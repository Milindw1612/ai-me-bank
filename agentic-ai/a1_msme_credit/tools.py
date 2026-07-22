"""External adapters for A1 — OCR, Credit Bureau, GST, Account Aggregator."""
import httpx

from shared.config import settings


# ── Financial Document OCR ─────────────────────────────────────────────────

async def ocr_extract_financials(document_urls: list[str]) -> dict:
    """OCR-extracts ITRs, P&L, balance sheets into structured financials per fiscal year."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.ocr_api_url}/extract/financials",
            headers={"Authorization": f"Bearer {settings.ocr_api_key}"},
            json={"document_urls": document_urls},
        )
        resp.raise_for_status()
        return resp.json()["financials"]


# ── Credit Bureau (CIBIL) ───────────────────────────────────────────────────

async def bureau_pull_score(applicant_token: str) -> dict:
    """Returns {score, report_ref, delinquencies, enquiries_6m}."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{settings.bureau_api_url}/score",
            params={"applicant_token": applicant_token},
            headers={"Authorization": f"Bearer {settings.bureau_api_key}"},
        )
        resp.raise_for_status()
        return resp.json()


# ── GST Returns ─────────────────────────────────────────────────────────────

async def gstr_fetch_returns(applicant_token: str) -> dict:
    """Returns GSTR-1/3B filing status and declared turnover for the last 12 months."""
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{settings.gst_api_url}/returns",
            params={"applicant_token": applicant_token, "months": 12},
            headers={"Authorization": f"Bearer {settings.gst_api_key}"},
        )
        resp.raise_for_status()
        return resp.json()


# ── Account Aggregator (bank feed) ─────────────────────────────────────────

async def aa_fetch_bank_feed(consent_token: str) -> dict:
    """Returns read-only transaction summary via AA consent — average balance, inflow/outflow, bounce count."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(
            f"{settings.aa_base_url}/fi/data",
            params={"consent_token": consent_token},
            headers={"Authorization": f"Bearer {await _aa_token()}"},
        )
        resp.raise_for_status()
        return resp.json()["summary"]


async def _aa_token() -> str:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.aa_base_url}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.aa_client_id,
                "client_secret": settings.aa_client_secret,
            },
        )
        resp.raise_for_status()
        return resp.json()["access_token"]


# ── CAM Document Generation ─────────────────────────────────────────────────

async def cam_generate_document(payload: dict) -> str:
    """Renders the Credit Appraisal Memo to PDF and returns a storage ref."""
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{settings.cbs_base_url}/documents/cam",
            headers={"Authorization": f"Bearer {settings.cbs_client_secret}"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["document_ref"]
