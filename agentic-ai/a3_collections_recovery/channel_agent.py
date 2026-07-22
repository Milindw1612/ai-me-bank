"""Channel Agent — SMS/WhatsApp/voice selection based on propensity score and DPD bucket."""
from a3_collections_recovery.states import CollectionsState


async def run(state: CollectionsState) -> CollectionsState:
    score = state["payment_propensity_score"]
    dpd = state["dpd_bucket"]

    if score >= 70:
        channel = "whatsapp"        # high propensity — low-friction nudge
    elif score >= 40 or dpd == "1-30":
        channel = "sms"             # medium propensity / early bucket — lightweight reminder
    else:
        channel = "voice"           # low propensity / later bucket — needs a live conversation

    return {**state, "selected_channel": channel, "channel_done": True, "current_step": "channel_selection"}
