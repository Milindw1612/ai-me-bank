"""External adapters for A3 — bureau payment history, outreach channels, core banking PTP recording."""
import httpx

from shared.config import settings


# ── Payment History (bureau) ────────────────────────────────────────────────

async def bureau_payment_history(customer_token: str) -> float:
    """Returns a 0-100 payment propensity score from historical repayment behavior."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.bureau_api_url}/payment-history",
            params={"customer_token": customer_token},
            headers={"Authorization": f"Bearer {settings.bureau_api_key}"},
        )
        resp.raise_for_status()
        return resp.json()["propensity_score"]


# ── Outreach Channels ────────────────────────────────────────────────────────

async def sms_send_reminder(phone_token: str, message: str) -> bool:
    from shared.middleware import decrypt_pii
    phone = decrypt_pii(phone_token)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.sms_gateway_url}/send",
            headers={"Authorization": f"Bearer {settings.sms_gateway_key}"},
            json={"to": phone, "message": message},
        )
        return resp.status_code == 200


async def whatsapp_send_reminder(phone_token: str, message: str, template: str = "collections_reminder") -> bool:
    from shared.middleware import decrypt_pii
    phone = decrypt_pii(phone_token)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://graph.facebook.com/v20.0/{settings.whatsapp_phone_number_id}/messages",
            headers={"Authorization": f"Bearer {settings.whatsapp_api_token}"},
            json={
                "messaging_product": "whatsapp",
                "to": phone,
                "type": "template",
                "template": {
                    "name": template,
                    "language": {"code": "en_IN"},
                    "components": [{"type": "body", "parameters": [{"type": "text", "text": message}]}],
                },
            },
        )
        return resp.status_code == 200


async def ivr_trigger_call(phone_token: str, script_id: str) -> bool:
    from shared.middleware import decrypt_pii
    phone = decrypt_pii(phone_token)
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.ivr_api_url}/calls",
            headers={"Authorization": f"Bearer {settings.ivr_api_key}"},
            json={"to": phone, "script_id": script_id},
        )
        return resp.status_code == 200


# ── Negotiation / Core Banking ──────────────────────────────────────────────

async def core_banking_record_ptp(account_id: str, promise_date: str, promise_amount: float) -> bool:
    """Records a Promise-to-Pay commitment against the account."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.cbs_base_url}/accounts/{account_id}/promise-to-pay",
            headers={"Authorization": f"Bearer {settings.cbs_client_secret}"},
            json={"promise_date": promise_date, "promise_amount": promise_amount},
        )
        return resp.status_code == 200
