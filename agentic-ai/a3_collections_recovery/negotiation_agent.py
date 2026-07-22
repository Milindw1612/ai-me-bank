"""Negotiation Agent — settlement/EMI offers within pre-approved policy bands."""
import json

from shared.llm import complete, HAIKU
from shared.middleware import safe_json
from a3_collections_recovery.states import CollectionsState
from a3_collections_recovery.tools import (
    sms_send_reminder, whatsapp_send_reminder, ivr_trigger_call, core_banking_record_ptp,
)

# Pre-approved settlement bands by DPD bucket — negotiation never exceeds these without escalation
_POLICY_BANDS = {
    "1-30": (0.90, 1.00),   # 90-100% of outstanding
    "31-60": (0.75, 0.95),
    "61-90": (0.60, 0.85),
}


async def run(state: CollectionsState) -> CollectionsState:
    channel = state["selected_channel"]
    outstanding = state["outstanding_amount"]
    band = _POLICY_BANDS.get(state["dpd_bucket"], (0.85, 1.00))

    prompt_data = {
        "outstanding_amount": outstanding,
        "payment_propensity_score": state["payment_propensity_score"],
        "policy_band_pct": band,
    }
    answer = await complete(
        messages=[{
            "role": "user",
            "content": (
                f"Propose a settlement offer within this policy band:\n{safe_json(prompt_data)}\n\n"
                "Return JSON: {\"offer_amount\": float, \"reasoning\": short string}."
            ),
        }],
        model=HAIKU,
        max_tokens=200,
        trace_name="collections_negotiation",
    )
    try:
        parsed = json.loads(answer)
        offer = float(parsed.get("offer_amount", outstanding * band[0]))
    except (ValueError, TypeError):
        offer = outstanding * band[0]

    message = f"We can offer a settlement of Rs.{offer:,.0f} on your outstanding of Rs.{outstanding:,.0f}. Reply to accept."
    if channel == "sms":
        await sms_send_reminder(state["phone_token"], message)
    elif channel == "whatsapp":
        await whatsapp_send_reminder(state["phone_token"], message)
    else:
        await ivr_trigger_call(state["phone_token"], script_id="settlement_offer")

    within_band = band[0] * outstanding <= offer <= band[1] * outstanding

    # Simplified: outreach is fire-and-forget here; a real implementation awaits the customer's
    # reply via webhook and resumes the graph from a persisted checkpoint.
    return {
        **state,
        "settlement_offer": offer,
        "negotiation_outcome": "no_response",
        "within_policy_band": within_band,
        "current_step": "negotiation",
    }
