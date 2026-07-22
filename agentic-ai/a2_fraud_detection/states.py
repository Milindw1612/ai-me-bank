from typing import TypedDict, Optional, Literal


class FraudState(TypedDict, total=False):
    # Input
    case_id: str
    transaction_token: str
    customer_token: str
    channel: Literal["card", "upi", "imps"]
    amount: float
    device_id_token: str
    ip_address: str
    merchant_token: str
    beneficiary_token: str

    # Device/IP & Network Agent output
    device_risk_score: float
    ip_reputation_score: float
    device_ip_done: bool

    # Behavior Pattern Agent output
    velocity_anomaly: bool
    spend_pattern_score: float
    behavior_done: bool

    # Merchant/Beneficiary & AML Agent output
    merchant_risk_score: float
    aml_watchlist_hit: bool
    aml_done: bool

    # Recommendation Agent output (joins all 3 above)
    fraud_probability: float
    reasons: list[str]
    recommended_action: Literal["freeze", "clear", "escalate"]
    scored_in_ms: int

    # Human sign-off (only when escalated)
    analyst_token: str
    final_decision: Optional[Literal["cleared", "confirmed_fraud"]]

    # LangGraph internal
    current_step: str
    error: Optional[str]
