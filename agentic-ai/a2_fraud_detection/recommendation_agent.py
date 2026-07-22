"""Recommendation Agent — joins Device/IP + Behavior + Merchant/AML, produces a fraud-probability score with reasons in under 60 seconds."""
import json
import time

from shared.llm import complete, HAIKU
from shared.middleware import safe_json
from a2_fraud_detection.states import FraudState


async def run(state: FraudState) -> FraudState:
    started = time.monotonic()

    signals = {
        "device_risk_score": state["device_risk_score"],
        "ip_reputation_score": state["ip_reputation_score"],
        "velocity_anomaly": state["velocity_anomaly"],
        "spend_pattern_score": state["spend_pattern_score"],
        "merchant_risk_score": state["merchant_risk_score"],
        "aml_watchlist_hit": state["aml_watchlist_hit"],
        "amount": state["amount"],
        "channel": state["channel"],
    }

    answer = await complete(
        messages=[{
            "role": "user",
            "content": (
                f"Score this transaction's fraud probability from combined signals:\n{safe_json(signals)}\n\n"
                "Return JSON: {\"fraud_probability\": 0-1 float, \"reasons\": [short strings], "
                "\"recommended_action\": \"freeze\"|\"clear\"|\"escalate\"}.\n"
                "Rules: aml_watchlist_hit=true -> always freeze. fraud_probability>0.7 -> freeze. "
                "0.3-0.7 -> escalate to analyst. <0.3 -> clear."
            ),
        }],
        model=HAIKU,
        max_tokens=300,
        trace_name="fraud_recommendation",
    )

    try:
        parsed = json.loads(answer)
    except ValueError:
        parsed = {"fraud_probability": 0.5, "reasons": ["parse_error_defaulted_to_escalate"], "recommended_action": "escalate"}

    elapsed_ms = int((time.monotonic() - started) * 1000)

    return {
        **state,
        "fraud_probability": parsed.get("fraud_probability", 0.5),
        "reasons": parsed.get("reasons", []),
        "recommended_action": parsed.get("recommended_action", "escalate"),
        "scored_in_ms": elapsed_ms,
        "current_step": "recommendation",
    }
