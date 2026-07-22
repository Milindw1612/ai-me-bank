"""Risk/Behavior Agent — payment history scoring."""
from a3_collections_recovery.states import CollectionsState
from a3_collections_recovery.tools import bureau_payment_history


async def run(state: CollectionsState) -> CollectionsState:
    score = await bureau_payment_history(state["customer_token"])
    return {**state, "payment_propensity_score": score, "risk_behavior_done": True, "current_step": "risk_behavior_scoring"}
