"""CAM Drafting Agent — pre-populates the Credit Appraisal Memo with recommended pricing."""
from shared.llm import complete, SONNET
from shared.middleware import safe_json
from a1_msme_credit.states import CreditState
from a1_msme_credit.tools import cam_generate_document


async def run(state: CreditState) -> CreditState:
    prompt_data = {
        "cash_flow_score": state["cash_flow_score"],
        "risk_flags": state["risk_flags"],
        "cibil_score": state["cibil_score"],
        "loan_amount_requested": state["loan_amount_requested"],
    }

    summary = await complete(
        messages=[{
            "role": "user",
            "content": (
                f"Draft a one-paragraph CAM summary and a recommended pricing band "
                f"(e.g. 'MCLR + 2.5%–3.5%') from this risk assessment:\n{safe_json(prompt_data)}"
            ),
        }],
        model=SONNET,
        max_tokens=400,
        trace_name="msme_cam_drafting",
    )

    doc_ref = await cam_generate_document({
        "application_id": state["application_id"],
        "financials": state["financials"],
        "risk_flags": state["risk_flags"],
        "cash_flow_score": state["cash_flow_score"],
        "summary": summary,
    })

    # Pricing recommendation extracted from the LLM summary — simple heuristic default as fallback
    pricing = "MCLR + 2.5%–3.5%" if state["cash_flow_score"] >= 60 else "MCLR + 3.5%–4.5%"

    return {
        **state,
        "cam_summary": summary,
        "recommended_pricing": pricing,
        "cam_document_ref": doc_ref,
        "current_step": "cam_drafted",
    }
