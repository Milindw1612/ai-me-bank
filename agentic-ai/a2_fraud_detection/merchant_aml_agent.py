"""Merchant/Beneficiary & AML Agent — merchant risk, AML watchlists."""
from a2_fraud_detection.states import FraudState
from a2_fraud_detection.tools import merchant_risk_lookup, aml_watchlist_check


async def run(state: FraudState) -> FraudState:
    merchant_score = await merchant_risk_lookup(state["merchant_token"])
    aml_hit = await aml_watchlist_check(state["beneficiary_token"])
    return {
        **state,
        "merchant_risk_score": merchant_score,
        "aml_watchlist_hit": aml_hit,
        "aml_done": True,
        "current_step": "merchant_aml_check",
    }
