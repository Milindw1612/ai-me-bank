from typing import TypedDict, Optional, Literal


class CollectionsState(TypedDict, total=False):
    # Input
    account_id: str
    customer_token: str
    dpd_bucket: str               # e.g. "1-30", "31-60", "61-90"
    outstanding_amount: float
    phone_token: str

    # Risk/Behavior Agent output
    payment_propensity_score: float
    risk_behavior_done: bool

    # Channel Agent output
    selected_channel: Literal["sms", "whatsapp", "voice"]
    channel_done: bool

    # Negotiation Agent output
    settlement_offer: float
    negotiation_outcome: Literal["accepted", "counter_offered", "declined", "no_response"]
    within_policy_band: bool

    # Escalation Agent output (only when negotiation fails or is aggressive)
    escalation_flag: bool
    escalation_reason: str

    # Human sign-off
    collections_officer_token: str
    final_outcome: Optional[Literal["settled", "promise_to_pay", "unresolved"]]

    # LangGraph internal
    current_step: str
    error: Optional[str]
