"""Device/IP & Network Agent — device fingerprint, IP reputation."""
from a2_fraud_detection.states import FraudState
from a2_fraud_detection.tools import device_fingerprint_lookup, ip_reputation_check


async def run(state: FraudState) -> FraudState:
    device_score = await device_fingerprint_lookup(state["device_id_token"])
    ip_score = await ip_reputation_check(state["ip_address"])
    return {
        **state,
        "device_risk_score": device_score,
        "ip_reputation_score": ip_score,
        "device_ip_done": True,
        "current_step": "device_ip_check",
    }
