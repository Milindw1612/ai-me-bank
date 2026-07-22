"""Credit Orchestrator Agent — fan-out to Financial Ingestion + Bureau/Tax, join into Risk & Cash-Flow, then CAM Drafting."""
import uuid
from langgraph.graph import StateGraph, END

from a1_msme_credit.states import CreditState
from a1_msme_credit import financial_ingestion_agent, bureau_tax_agent, risk_cashflow_agent, cam_drafting_agent


def build_credit_graph() -> StateGraph:
    g = StateGraph(CreditState)

    g.add_node("financial_ingestion", financial_ingestion_agent.run)
    g.add_node("bureau_tax_verification", bureau_tax_agent.run)
    g.add_node("risk_cashflow", risk_cashflow_agent.run)
    g.add_node("cam_drafting", cam_drafting_agent.run)

    # Fan-out: financial ingestion and bureau/tax verification run independently
    g.set_entry_point("financial_ingestion")
    g.add_edge("financial_ingestion", "bureau_tax_verification")

    # Join: risk & cash-flow needs both financial data and bureau/tax data
    g.add_edge("bureau_tax_verification", "risk_cashflow")
    g.add_edge("risk_cashflow", "cam_drafting")
    g.add_edge("cam_drafting", END)

    return g.compile()


credit_graph = build_credit_graph()


async def process_credit_application(payload: dict) -> dict:
    application_id = payload.get("application_id", str(uuid.uuid4()))
    initial_state: CreditState = {
        "application_id": application_id,
        "applicant_token": payload["applicant_token"],
        "loan_amount_requested": float(payload["loan_amount_requested"]),
        "business_vintage_years": float(payload.get("business_vintage_years", 0)),
        "document_urls": payload.get("document_urls", []),
        "current_step": "start",
    }
    result = await credit_graph.ainvoke(initial_state)
    return {
        "application_id": application_id,
        "status": "awaiting_signoff",
        "recommended_pricing": result.get("recommended_pricing"),
        "cam_document_ref": result.get("cam_document_ref"),
        "risk_flags": result.get("risk_flags", []),
    }
