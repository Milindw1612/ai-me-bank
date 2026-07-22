"""External adapters for A2 — device/IP intelligence, transaction feed, AML watchlist, core banking actions."""
import httpx

from shared.config import settings


# ── Device / IP Intelligence ────────────────────────────────────────────────

async def device_fingerprint_lookup(device_id_token: str) -> float:
    """Returns a 0-100 device risk score (jailbreak/emulator/known-fraud-device signals)."""
    async with httpx.AsyncClient(timeout=8) as client:
        resp = await client.get(
            f"{settings.txn_feed_api_url}/device-risk",
            params={"device_token": device_id_token},
            headers={"Authorization": f"Bearer {settings.txn_feed_api_key}"},
        )
        resp.raise_for_status()
        return resp.json()["risk_score"]


async def ip_reputation_check(ip_address: str) -> float:
    """Returns a 0-100 IP reputation risk score (VPN/proxy/TOR/known-bad-IP signals)."""
    async with httpx.AsyncClient(timeout=8) as client:
        resp = await client.get(
            f"{settings.txn_feed_api_url}/ip-reputation",
            params={"ip": ip_address},
            headers={"Authorization": f"Bearer {settings.txn_feed_api_key}"},
        )
        resp.raise_for_status()
        return resp.json()["risk_score"]


# ── Behavior / Velocity ─────────────────────────────────────────────────────

async def velocity_check(customer_token: str, amount: float, channel: str) -> dict:
    """Returns {anomaly: bool, spend_pattern_score: float} vs. the customer's rolling 90-day baseline."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.txn_feed_api_url}/velocity-check",
            headers={"Authorization": f"Bearer {settings.txn_feed_api_key}"},
            json={"customer_token": customer_token, "amount": amount, "channel": channel},
        )
        resp.raise_for_status()
        return resp.json()


# ── Merchant / Beneficiary / AML ────────────────────────────────────────────

async def merchant_risk_lookup(merchant_token: str) -> float:
    async with httpx.AsyncClient(timeout=8) as client:
        resp = await client.get(
            f"{settings.txn_feed_api_url}/merchant-risk",
            params={"merchant_token": merchant_token},
            headers={"Authorization": f"Bearer {settings.txn_feed_api_key}"},
        )
        resp.raise_for_status()
        return resp.json()["risk_score"]


async def aml_watchlist_check(beneficiary_token: str) -> bool:
    """Screens beneficiary against sanctions/PEP/adverse-media watchlists."""
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{settings.aml_watchlist_api_url}/screen",
            params={"beneficiary_token": beneficiary_token},
            headers={"Authorization": f"Bearer {settings.aml_watchlist_api_key}"},
        )
        resp.raise_for_status()
        return resp.json()["hit"]


# ── Core Banking Actions ─────────────────────────────────────────────────────

async def core_banking_freeze_transaction(transaction_token: str) -> bool:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.cbs_base_url}/transactions/{transaction_token}/freeze",
            headers={"Authorization": f"Bearer {settings.cbs_client_secret}"},
        )
        return resp.status_code == 200


async def core_banking_clear_transaction(transaction_token: str) -> bool:
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{settings.cbs_base_url}/transactions/{transaction_token}/clear",
            headers={"Authorization": f"Bearer {settings.cbs_client_secret}"},
        )
        return resp.status_code == 200
