from typing import TypedDict, Optional, Literal


class CreditState(TypedDict, total=False):
    # Input
    application_id: str
    applicant_token: str          # PAN/GSTIN tokenised — never raw in prompts
    loan_amount_requested: float
    business_vintage_years: float
    document_urls: list[str]      # ITRs, P&L, balance sheets to OCR

    # Financial Ingestion Agent output
    financials: dict              # {revenue, expenses, net_margin, ...} per fiscal year
    financial_ingestion_done: bool

    # Bureau & Tax Verification Agent output
    cibil_score: int
    gstr_filed_ok: bool
    gstr_summary: dict
    aa_bank_feed_summary: dict
    bureau_tax_done: bool

    # Risk & Cash-Flow Agent output (joins financial_ingestion + bureau_tax)
    cash_flow_score: float
    risk_flags: list[str]
    anomaly_detected: bool
    risk_notes: str
    policy_refs: list[str]     # RBI/internal credit policy sources cited by the RAG

    # CAM Drafting Agent output
    recommended_pricing: str
    cam_document_ref: str
    cam_summary: str

    # Human sign-off
    credit_officer_token: str
    signoff_decision: Optional[Literal["approved", "rejected"]]
    signoff_notes: str

    # LangGraph internal
    current_step: str
    error: Optional[str]
