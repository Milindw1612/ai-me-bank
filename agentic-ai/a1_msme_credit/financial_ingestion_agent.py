"""Financial Ingestion Agent — OCR: ITRs, P&L, balance sheets."""
from a1_msme_credit.states import CreditState
from a1_msme_credit.tools import ocr_extract_financials


async def run(state: CreditState) -> CreditState:
    financials = await ocr_extract_financials(state["document_urls"])
    return {**state, "financials": financials, "financial_ingestion_done": True, "current_step": "financial_ingestion"}
