"""Escalation Agent — flags complex/aggressive cases with full context for a human collections officer."""
from a3_collections_recovery.states import CollectionsState


async def run(state: CollectionsState) -> CollectionsState:
    outcome = state.get("negotiation_outcome")
    reason = {
        "declined": "Customer explicitly declined the settlement offer.",
        "no_response": "No response received within the negotiation window.",
    }.get(outcome, "Negotiation outside pre-approved policy band — requires manual review.")

    return {
        **state,
        "escalation_flag": True,
        "escalation_reason": reason,
        "current_step": "escalated",
    }
