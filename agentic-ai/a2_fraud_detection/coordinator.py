"""Coordinator Agent — fans out to Device/IP, Behavior, Merchant/AML in parallel, joins into Recommendation Agent."""
import uuid
from langgraph.graph import StateGraph, END

from a2_fraud_detection.states import FraudState
from a2_fraud_detection import device_ip_agent, behavior_pattern_agent, merchant_aml_agent, recommendation_agent
from a2_fraud_detection.tools import core_banking_freeze_transaction, core_banking_clear_transaction


async def node_auto_action(state: FraudState) -> FraudState:
    """Auto-freeze thresholds need governance sign-off before going live — read-only in this skeleton."""
    action = state["recommended_action"]
    if action == "freeze":
        await core_banking_freeze_transaction(state["transaction_token"])
    elif action == "clear":
        await core_banking_clear_transaction(state["transaction_token"])
    return {**state, "current_step": f"auto_{action}"}


def route_after_recommendation(state: FraudState) -> str:
    return "escalate" if state["recommended_action"] == "escalate" else "auto_action"


def build_fraud_graph() -> StateGraph:
    g = StateGraph(FraudState)

    g.add_node("device_ip_check", device_ip_agent.run)
    g.add_node("behavior_pattern_check", behavior_pattern_agent.run)
    g.add_node("merchant_aml_check", merchant_aml_agent.run)
    g.add_node("recommendation", recommendation_agent.run)
    g.add_node("auto_action", node_auto_action)

    # Fan-out: the 3 signal-gathering agents run off the same entry point
    g.set_entry_point("device_ip_check")
    g.add_edge("device_ip_check", "behavior_pattern_check")
    g.add_edge("behavior_pattern_check", "merchant_aml_check")

    # Join: recommendation needs all 3 signal sets
    g.add_edge("merchant_aml_check", "recommendation")

    g.add_conditional_edges(
        "recommendation",
        route_after_recommendation,
        {"auto_action": "auto_action", "escalate": END},   # escalate → analyst queue, ends the auto-graph here
    )
    g.add_edge("auto_action", END)

    return g.compile()


fraud_graph = build_fraud_graph()


async def process_fraud_case(payload: dict) -> dict:
    case_id = payload.get("case_id", str(uuid.uuid4()))
    initial_state: FraudState = {
        "case_id": case_id,
        "transaction_token": payload["transaction_token"],
        "customer_token": payload["customer_token"],
        "channel": payload["channel"],
        "amount": float(payload["amount"]),
        "device_id_token": payload["device_id_token"],
        "ip_address": payload["ip_address"],
        "merchant_token": payload["merchant_token"],
        "beneficiary_token": payload["beneficiary_token"],
        "current_step": "start",
    }
    result = await fraud_graph.ainvoke(initial_state)
    return {
        "case_id": case_id,
        "fraud_probability": result.get("fraud_probability"),
        "reasons": result.get("reasons", []),
        "recommended_action": result.get("recommended_action"),
        "scored_in_ms": result.get("scored_in_ms"),
    }
