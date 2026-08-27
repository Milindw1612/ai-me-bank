# -*- coding: utf-8 -*-
"""
Stage A: rule-based risk scoring across all 10,000 synthetic transactions
          (no API calls -- fast, free, deterministic).
Stage B: batched Gemini calls for only the flagged/borderline subset,
          generating real natural-language fraud-analyst reasoning.

Requires: GEMINI_API_KEY environment variable (never written to a file).

Run: GEMINI_API_KEY=xxxx python score_transactions.py
Output: results.json
"""
import json
import os
import re
import time
import urllib.request
import urllib.error
from collections import Counter, defaultdict

RISKY_MERCHANTS = {
    "Crypto Exchange - OffshoreX", "QuickCash Lending Ltd",
    "Unverified Marketplace Seller", "Forex Remit - Unlisted",
    "Gaming Wallet Topup - Unverified", "Shell Trading Co",
}

FLAG_THRESHOLD = 45
BATCH_SIZE = 35
MODEL = "models/gemini-3.5-flash"
API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def build_account_profiles(records):
    by_account = defaultdict(list)
    for r in records:
        by_account[r["account_id"]].append(r)

    profiles = {}
    for acc_id, txns in by_account.items():
        device_counts = Counter(t["device_id"] for t in txns)
        country_counts = Counter(t["ip_country"] for t in txns)
        profiles[acc_id] = {
            "usual_device": device_counts.most_common(1)[0][0],
            "usual_country": country_counts.most_common(1)[0][0],
        }
    return profiles


def score_record(r, profile):
    signals = []
    score = 0

    ratio = r["amount"] / max(r["prior_avg_txn_amount"], 1)
    if ratio >= 8:
        score += 55
        signals.append(f"amount {ratio:.1f}x above account average")
    elif ratio >= 4:
        score += 35
        signals.append(f"amount {ratio:.1f}x above account average")
    elif ratio >= 2.5:
        score += 18
        signals.append(f"amount {ratio:.1f}x above account average")

    if r["device_id"] != profile["usual_device"]:
        score += 30
        signals.append("transaction from an unrecognized device")

    hour = int(r["timestamp"][11:13])
    if 1 <= hour <= 4:
        score += 20
        signals.append(f"unusual transaction hour ({hour:02d}:00)")

    if r["ip_country"] != profile["usual_country"]:
        score += 40
        signals.append(f"IP geography mismatch ({r['ip_country']}, usually {profile['usual_country']})")

    if r["merchant"] in RISKY_MERCHANTS:
        score += 40
        signals.append(f"high-risk merchant category ({r['merchant']})")

    return min(score, 100), signals


def call_gemini_batch(api_key, batch):
    prompt_lines = [
        "You are the Recommendation Agent in a bank's Fraud Detection pipeline. "
        "Below are transactions flagged by a rule-based risk-signal layer for review. "
        "For EACH transaction, write a short (1-2 sentence) analyst-style reasoning "
        "explaining why it looks suspicious given its signals, and recommend exactly "
        "one action: \"Auto-freeze\" (high confidence fraud), \"Route to Analyst\" "
        "(mid confidence, needs human review), or \"Clear\" (signals present but "
        "likely benign on reflection). Respond ONLY with a JSON array, one object "
        "per transaction, each with keys: transaction_id, reasoning, action, confidence "
        "(a number 0-100). No prose outside the JSON array.",
        "",
        "Transactions:",
    ]
    for r, score, signals in batch:
        prompt_lines.append(json.dumps({
            "transaction_id": r["transaction_id"],
            "amount": r["amount"],
            "channel": r["channel"],
            "merchant": r["merchant"],
            "risk_score": score,
            "signals": signals,
        }))
    prompt = "\n".join(prompt_lines)

    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3},
    }).encode("utf-8")

    url = f"{API_BASE}/{MODEL}:generateContent?key={api_key}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")

    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
            return json.loads(text)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            # Retry on any transient/rate-limit error (429, 500, 502, 503, 504),
            # not just 429 -- a bare 503 (model overloaded) was previously
            # returned as a permanent failure after a single try.
            if e.code in (429, 500, 502, 503, 504) and attempt < 4:
                time.sleep(6 * (attempt + 1))
                continue
            print(f"  HTTP {e.code} error: {err_body[:300]}")
            return []
        except Exception as e:
            print(f"  Batch error: {e}")
            if attempt < 2:
                time.sleep(4)
                continue
            return []
    return []


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("Set GEMINI_API_KEY environment variable before running.")

    with open("transactions.json", encoding="utf-8") as f:
        records = json.load(f)

    profiles = build_account_profiles(records)

    flagged = []
    for r in records:
        score, signals = score_record(r, profiles[r["account_id"]])
        r["risk_score"] = score
        r["signals"] = signals
        r["flagged"] = score >= FLAG_THRESHOLD
        if r["flagged"]:
            flagged.append(r)

    print(f"Stage A complete: {len(records)} scored, {len(flagged)} flagged (threshold >= {FLAG_THRESHOLD})")

    caught = sum(1 for r in flagged if r["injected_fraud_pattern"])
    total_injected = sum(1 for r in records if r["injected_fraud_pattern"])
    print(f"  Injected fraud patterns caught: {caught}/{total_injected} ({caught/max(total_injected,1)*100:.1f}%)")
    print(f"  False positives (flagged, no injected pattern): {len(flagged) - caught}")

    # Stage B: batched Gemini reasoning for the flagged subset only
    n_batches = (len(flagged) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"\nStage B: {len(flagged)} flagged records -> {n_batches} Gemini batch calls...")

    reasoning_by_id = {}
    for i in range(0, len(flagged), BATCH_SIZE):
        chunk = flagged[i:i + BATCH_SIZE]
        batch_input = [(r, r["risk_score"], r["signals"]) for r in chunk]
        batch_num = i // BATCH_SIZE + 1
        print(f"  Batch {batch_num}/{n_batches} ({len(chunk)} records)...", end=" ")
        result = call_gemini_batch(api_key, batch_input)
        ok = 0
        for item in result:
            tid = item.get("transaction_id")
            if tid:
                reasoning_by_id[tid] = {
                    "reasoning": item.get("reasoning", ""),
                    "action": item.get("action", "Route to Analyst"),
                    "confidence": item.get("confidence", 50),
                }
                ok += 1
        print(f"got {ok}/{len(chunk)}")
        time.sleep(2)  # gentle pacing for free-tier rate limits

    for r in flagged:
        rb = reasoning_by_id.get(r["transaction_id"])
        if rb:
            r["reasoning"] = rb["reasoning"]
            r["recommended_action"] = rb["action"]
            r["confidence"] = rb["confidence"]
        else:
            r["reasoning"] = "Flagged by rule-based signals; detailed reasoning unavailable for this record."
            r["recommended_action"] = "Route to Analyst"
            r["confidence"] = 50

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=None, separators=(",", ":"))

    n_with_reasoning = sum(1 for r in flagged if r["transaction_id"] in reasoning_by_id)
    print(f"\nDone. results.json written. {n_with_reasoning}/{len(flagged)} flagged records got Gemini reasoning.")


if __name__ == "__main__":
    main()
