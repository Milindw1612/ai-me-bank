"""Coordinator Agent — sequences outreach, negotiates within pre-approved bands, escalates only complex/aggressive cases."""
import uuid
from langgraph.graph import StateGraph, END

from a3_collections_recovery.states import CollectionsState
from a3_collections_recovery import risk_behavior_agent, channel_agent, negotiation_agent, escalation_agent


def route_after_negotiation(state: CollectionsState) -> str:
    if state["negotiation_outcome"] == "accepted" and state["within_policy_band"]:
        return "resolved"
    return "escalation"


def build_collections_graph() -> StateGraph:
    g = StateGraph(CollectionsState)

    g.add_node("risk_behavior_scoring", risk_behavior_agent.run)
    g.add_node("channel_selection", channel_agent.run)
    g.add_node("negotiation", negotiation_agent.run)
    g.add_node("escalation", escalation_agent.run)

    g.set_entry_point("risk_behavior_scoring")
    g.add_edge("risk_behavior_scoring", "channel_selection")
    g.add_edge("channel_selection", "negotiation")
    g.add_conditional_edges(
        "negotiation",
        route_after_negotiation,
        {"resolved": END, "escalation": "escalation"},
    )
    g.add_edge("escalation", END)

    return g.compile()


collections_graph = build_collections_graph()


async def process_collections_account(payload: dict) -> dict:
    account_id = payload.get("account_id", str(uuid.uuid4()))
    initial_state: CollectionsState = {
        "account_id": account_id,
        "customer_token": payload["customer_token"],
        "dpd_bucket": payload["dpd_bucket"],
        "outstanding_amount": float(payload["outstanding_amount"]),
        "phone_token": payload["phone_token"],
        "current_step": "start",
    }
    result = await collections_graph.ainvoke(initial_state)
    return {
        "account_id": account_id,
        "selected_channel": result.get("selected_channel"),
        "settlement_offer": result.get("settlement_offer"),
        "negotiation_outcome": result.get("negotiation_outcome"),
        "escalation_flag": result.get("escalation_flag", False),
        "escalation_reason": result.get("escalation_reason"),
    }
