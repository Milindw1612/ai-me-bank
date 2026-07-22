"""Behavior Pattern Agent — spend/velocity anomaly detection."""
from a2_fraud_detection.states import FraudState
from a2_fraud_detection.tools import velocity_check


async def run(state: FraudState) -> FraudState:
    result = await velocity_check(state["customer_token"], state["amount"], state["channel"])
    return {
        **state,
        "velocity_anomaly": result.get("anomaly", False),
        "spend_pattern_score": result.get("spend_pattern_score", 0.0),
        "behavior_done": True,
        "current_step": "behavior_pattern_check",
    }
