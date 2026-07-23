"""Risk & Cash-Flow Agent — joins Financial Ingestion + Bureau/Tax, flags anomalies via Claude Sonnet.
Grounds its risk assessment in RBI Master Directions + internal credit policy via the shared RAG."""
from shared.llm import complete, SONNET
from shared.middleware import safe_json
from shared.rag import policy_qa
from a1_msme_credit.states import CreditState


async def run(state: CreditState) -> CreditState:
    prompt_data = {
        "financials": state["financials"],
        "cibil_score": state["cibil_score"],
        "gstr_filed_ok": state["gstr_filed_ok"],
        "aa_bank_feed_summary": state["aa_bank_feed_summary"],
        "loan_amount_requested": state["loan_amount_requested"],
        "business_vintage_years": state["business_vintage_years"],
    }

    policy_answer, policy_refs = await policy_qa(
        f"What RBI/internal credit policy limits apply to an MSME loan of this size and vintage: {safe_json(prompt_data)}"
    )

    answer = await complete(
        messages=[{
            "role": "user",
            "content": (
                f"Assess MSME credit risk from this data:\n{safe_json(prompt_data)}\n\n"
                f"Relevant policy guidance:\n{policy_answer}\n\n"
                "Return a JSON object with keys: cash_flow_score (0-100), risk_flags "
                "(list of short strings), anomaly_detected (bool), notes (one paragraph)."
            ),
        }],
        model=SONNET,
        max_tokens=512,
        trace_name="msme_risk_cashflow",
    )

    import json
    try:
        parsed = json.loads(answer)
    except ValueError:
        parsed = {"cash_flow_score": 50.0, "risk_flags": [], "anomaly_detected": False, "notes": answer}

    return {
        **state,
        "cash_flow_score": parsed.get("cash_flow_score", 50.0),
        "risk_flags": parsed.get("risk_flags", []),
        "anomaly_detected": parsed.get("anomaly_detected", False),
        "risk_notes": parsed.get("notes", ""),
        "policy_refs": policy_refs,
        "current_step": "risk_cashflow_review",
    }
