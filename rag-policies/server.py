# -*- coding: utf-8 -*-
"""
Local backend server for the two demo GUIs (Loan Application, Policy
Assistant). Exposes the full pipeline described in the plan:

  input -> PII tokenization -> (route) -> Hybrid RAG -> (rules, loan only)
  -> prompt assembly (PII-free) -> Watchdog pre-check -> Gemini
  -> Watchdog post-check -> de-tokenize -> response

Run: GEMINI_API_KEY=xxxx python server.py
Serves on http://localhost:5001
"""
import json
import os
import re
import urllib.error
import urllib.request

from flask import Flask, jsonify, request
from flask_cors import CORS

from hybrid_retrieval import HybridRetriever
from pii_tokenizer import strip_structured_pii, tokenize_free_text, detokenize
from rule_engine import evaluate as evaluate_loan
import watchdog

MODEL = "models/gemini-3.5-flash"
API_BASE = "https://generativelanguage.googleapis.com/v1beta"

app = Flask(__name__)
CORS(app)  # local demo only; the HTML pages are opened via file:// or a
           # different local port than this server

print("Loading Hybrid RAG retriever (embedding model + Chroma + BM25)...")
retriever = HybridRetriever()
print("Ready.")


def call_gemini(prompt: str, temperature=0.3):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable not set.")
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }).encode("utf-8")
    url = f"{API_BASE}/{MODEL}:generateContent?key={api_key}"
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["candidates"][0]["content"]["parts"][0]["text"].strip()


def format_chunks(chunks):
    return "\n\n".join(
        f"[{c['metadata']['doc_code']} clause {c['metadata']['clause']} - {c['metadata']['heading']}]\n{c['text']}"
        for c in chunks
    )


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


@app.route("/api/loan-eligibility", methods=["POST"])
def loan_eligibility():
    payload = request.get_json(force=True)
    request_id = payload.get("request_id", "loan-request")
    demo_mode = payload.get("demo_mode")  # None | "scenario2"

    # Step 1: strip identifying fields -- they never leave this function.
    clean_data = strip_structured_pii(payload)

    # Step 2: deterministic rule verdict (the actual decision-maker).
    rule_result = evaluate_loan(clean_data)

    # Step 3: Hybrid RAG retrieval, grounded in the reasons the rule engine cited.
    retrieval_query = "; ".join(rule_result["reasons"])[:300]
    chunks = retriever.retrieve(retrieval_query, "loan_policies", top_k=4)
    conf_ok, conf_reason = watchdog.check_retrieval_confidence(chunks)

    # Step 4: prompt assembly -- PII-free (clean_data has no name/PAN/Aadhaar/etc.)
    if demo_mode == "scenario2":
        # Deliberately looser instruction, used ONLY for this scripted demo
        # case, to show the Watchdog's rule/LLM consistency check catching
        # an LLM that drifts into softening a rejection.
        instruction = (
            "You are a friendly loan assistant. Explain the situation to the applicant in an "
            "encouraging tone, and feel free to note any mitigating factors that might still work in "
            "their favor, even if the formal verdict is unfavorable."
        )
    else:
        instruction = (
            "You are the CAM Drafting Agent's explanation layer. You do NOT decide eligibility -- a "
            "verdict has already been determined by the deterministic rule engine below. Your only job "
            "is to explain, in 2-4 sentences, WHY this verdict was reached, citing the specific policy "
            "clauses provided. Do not suggest the verdict could be different, do not soften a rejection, "
            "and do not imply any exception or override is possible."
        )

    prompt = (
        f"{instruction}\n\n"
        f"VERDICT (already decided, do not change): {rule_result['verdict']}\n"
        f"REASONS: {'; '.join(rule_result['reasons'])}\n"
        f"FOIR: {rule_result['foir_pct']}% (category max: {rule_result['foir_max']}%)\n\n"
        f"RELEVANT POLICY CLAUSES:\n{format_chunks(chunks)}"
    )

    # Step 5: Watchdog pre-check (defense-in-depth; structured path is
    # already PII-free by construction, but we still run this for
    # consistent logging and as a safety net against a future schema change).
    pre_check = watchdog.run_watchdog(stage="pre_llm_call", prompt=prompt, request_id=request_id)
    if pre_check["blocked"]:
        return jsonify({
            "escalated": True,
            "reason": "PII detected in outgoing prompt -- request blocked before reaching the LLM.",
            "watchdog_flags": pre_check["flags"],
            "verdict": rule_result["verdict"],
        }), 200

    # Step 6: LLM call.
    try:
        llm_explanation = call_gemini(prompt)
    except Exception as e:
        return jsonify({"error": f"LLM call failed: {e}"}), 502

    # Step 7: Watchdog post-check -- rule/LLM consistency.
    post_check = watchdog.run_watchdog(
        stage="post_llm_call", rule_verdict=rule_result["verdict"],
        llm_explanation=llm_explanation, request_id=request_id,
    )

    if post_check["blocked"]:
        return jsonify({
            "escalated": True,
            "reason": "Agent exceeded scope -- LLM explanation was inconsistent with the deterministic "
                      "verdict. Escalated for human review instead of shown.",
            "watchdog_flags": post_check["flags"],
            "verdict": rule_result["verdict"],
            "reasons": rule_result["reasons"],
        }), 200

    return jsonify({
        "escalated": False,
        "verdict": rule_result["verdict"],
        "reasons": rule_result["reasons"],
        "foir_pct": rule_result["foir_pct"],
        "llm_explanation": llm_explanation,
        "retrieved_clauses": [
            {"doc_code": c["metadata"]["doc_code"], "clause": c["metadata"]["clause"], "heading": c["metadata"]["heading"]}
            for c in chunks
        ],
        "retrieval_confidence_ok": conf_ok,
        "watchdog_flags": pre_check["flags"] + post_check["flags"],
        "human_review_note": "Draft -- Pending Credit Officer Review. This is not a final decision.",
    })


COLLECTIONS = ["loan_policies", "fraud_policies"]


@app.route("/api/policy-query", methods=["POST"])
def policy_query():
    payload = request.get_json(force=True)
    query = payload.get("query", "")
    request_id = payload.get("request_id", "policy-request")

    # Step 1: tokenize free text -- primary PII layer.
    tokenized_query, token_map = tokenize_free_text(query)

    # Step 2: route -- compare top-1 DENSE distance across collections
    # (comparable across corpora, unlike RRF scores which are only
    # meaningful within one collection's own rank positions), then run
    # full hybrid retrieval only on the winning collection.
    best_collection, best_distance = None, float("inf")
    for coll in COLLECTIONS:
        dist = retriever.dense_top_distance(tokenized_query, coll)
        if dist < best_distance:
            best_collection, best_distance = coll, dist

    best_chunks = retriever.retrieve(tokenized_query, best_collection, top_k=3)
    conf_ok, conf_reason = watchdog.check_retrieval_confidence(best_chunks)

    # Step 3: prompt assembly -- uses the TOKENIZED query (never the raw one).
    prompt = (
        "You are a policy assistant. Answer the user's question using ONLY the policy clauses provided "
        "below, citing the document code and clause number. If the clauses don't clearly answer the "
        "question, say so rather than guessing.\n\n"
        f"USER QUESTION: {tokenized_query}\n\n"
        f"RELEVANT POLICY CLAUSES:\n{format_chunks(best_chunks)}"
    )

    # Step 4: Watchdog pre-check -- THIS is where Scenario 1 actually gets
    # tested: if tokenize_free_text() missed something, it's still sitting
    # in `prompt` right now, and this re-scan is the last chance to catch it.
    pre_check = watchdog.run_watchdog(stage="pre_llm_call", prompt=prompt, request_id=request_id)
    if pre_check["blocked"]:
        return jsonify({
            "escalated": True,
            "reason": "PII detected in outgoing prompt -- request blocked before reaching the LLM.",
            "watchdog_flags": pre_check["flags"],
        }), 200

    if not conf_ok:
        return jsonify({
            "escalated": True,
            "reason": f"Escalated to Policy Team -- {conf_reason}",
            "watchdog_flags": [{"check": "retrieval_confidence", "result": "FAIL", "detail": conf_reason}],
        }), 200

    # Step 5: LLM call.
    try:
        raw_answer = call_gemini(prompt)
    except Exception as e:
        return jsonify({"error": f"LLM call failed: {e}"}), 502

    # Step 6: de-tokenize the response before it goes back to the browser.
    final_answer = detokenize(raw_answer, token_map)

    watchdog.log_event({"stage": "response_returned", "request_id": request_id, "collection": best_collection})

    return jsonify({
        "escalated": False,
        "collection_used": best_collection,
        "answer": final_answer,
        "retrieved_clauses": [
            {"doc_code": c["metadata"]["doc_code"], "clause": c["metadata"]["clause"], "heading": c["metadata"]["heading"]}
            for c in best_chunks
        ],
        "watchdog_flags": pre_check["flags"],
        "pii_tokens_detected": len(token_map),
    })


# ============================================================================
# Fraud Transaction Tracker -- reuses the same governed pattern as Loan:
# deterministic score (already computed) -> Hybrid RAG (fraud_policies) ->
# PII-free prompt assembly -> Watchdog pre-check -> Gemini -> Watchdog
# post-check -> de-tokenize -> response.
# ============================================================================
FRAUD_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "fraud_demo", "results.json")

print("Loading fraud transaction dataset...")
with open(FRAUD_DATA_PATH, encoding="utf-8") as f:
    _fraud_records = json.load(f)
FRAUD_BY_ID = {r["transaction_id"]: r for r in _fraud_records}
print(f"Loaded {len(FRAUD_BY_ID)} transactions.")


def account_reference_token(account_id: str) -> str:
    """Deterministic reference token -- same account always maps to the
    same token within this dataset, but the real account_id never
    travels past this function."""
    return f"REF-{abs(hash(account_id)) % 100000:05d}"


@app.route("/api/fraud-lookup", methods=["POST"])
def fraud_lookup():
    payload = request.get_json(force=True)
    txn_id = payload.get("transaction_id", "")
    request_id = payload.get("request_id", "fraud-request")
    live = bool(payload.get("live", False))

    record = FRAUD_BY_ID.get(txn_id)
    if not record:
        return jsonify({"error": f"Transaction {txn_id} not found."}), 404

    # Step 1: de-identify. customer_name and address are dropped entirely;
    # account_id is replaced with a stable reference token. Only the
    # reference token, risk score, and non-identifying transaction
    # attributes travel forward.
    ref_token = account_reference_token(record["account_id"])
    risk_score = record.get("risk_score", 0)
    flagged = record.get("flagged", False)
    signals = record.get("signals", [])

    # Step 2: this score was already computed deterministically for all
    # 10,000 records by score_transactions.py (Stage A) -- this endpoint
    # does not re-score, it only explains what was already decided.

    # Default path -- NO Gemini call. Stage B already pre-computed reasoning
    # for every flagged record (score_transactions.py); this returns that
    # instantly, at zero API cost. This is what a normal click uses, so
    # browsing the table never depends on live quota. Pass `"live": true`
    # to deliberately trigger a fresh Gemini call instead (see below).
    if not live:
        return jsonify({
            "escalated": False,
            "live_call": False,
            "transaction_id": txn_id,
            "account_reference": ref_token,
            "real_account_id": record["account_id"],
            "risk_score": risk_score,
            "flagged": flagged,
            "signals": signals,
            "llm_explanation": record.get("reasoning", "No pre-computed reasoning available for this record."),
            "recommended_action": record.get("recommended_action", "Route to Analyst"),
            "confidence": record.get("confidence", 50),
            "human_review_note": "Draft -- Pending Fraud Analyst Review. This is not a final determination.",
        })

    # Step 3: Hybrid RAG retrieval against fraud_policies, grounded in
    # the actual signals that fired for this transaction.
    retrieval_query = "; ".join(signals) if signals else f"transaction risk score {risk_score}"
    chunks = retriever.retrieve(retrieval_query, "fraud_policies", top_k=4)
    conf_ok, conf_reason = watchdog.check_retrieval_confidence(chunks)

    # Step 4: prompt assembly -- PII-free (reference token only, never the
    # real account_id; no customer name or address anywhere in this prompt).
    prompt = (
        "You are the Fraud Detection pipeline's explanation layer. You do NOT decide whether a "
        "transaction is flagged -- that has already been determined by the deterministic risk-scoring "
        "engine below. Your only job is to explain, in 2-4 sentences, WHY this transaction received "
        "this score, citing the specific policy clauses provided. Do not suggest the score or flagged "
        "status could be different, and do not clear a flagged transaction.\n\n"
        f"REFERENCE: {ref_token}\n"
        f"RISK SCORE: {risk_score} (FLAGGED: {flagged})\n"
        f"SIGNALS: {'; '.join(signals) if signals else 'none'}\n"
        f"AMOUNT: Rs. {record['amount']:,.2f} | CHANNEL: {record['channel']} | "
        f"ACCOUNT TYPE: {record.get('account_type', 'unknown')}\n\n"
        f"RELEVANT POLICY CLAUSES:\n{format_chunks(chunks)}"
    )

    # Step 5: Watchdog pre-check -- outgoing-prompt PII re-scan (defense-in-
    # depth; this prompt was built PII-free by construction, but the check
    # still runs for consistent logging and as a safety net).
    pre_check = watchdog.run_watchdog(stage="pre_llm_call", prompt=prompt, request_id=request_id)
    if pre_check["blocked"]:
        return jsonify({
            "escalated": True,
            "reason": "PII detected in outgoing prompt -- request blocked before reaching the LLM.",
            "watchdog_flags": pre_check["flags"],
        }), 200

    # Step 6: LLM call.
    try:
        llm_explanation = call_gemini(prompt)
    except Exception as e:
        return jsonify({"error": f"LLM call failed: {e}"}), 502

    # Step 7: Watchdog post-check -- rule/LLM consistency (does the
    # explanation contradict a Flagged verdict by clearing it?).
    verdict_label = "Not Eligible" if flagged else "Eligible"  # reuse the same consistency check semantics
    post_check = watchdog.run_watchdog(
        stage="post_llm_call", rule_verdict=verdict_label if flagged else None,
        llm_explanation=llm_explanation if flagged else None, request_id=request_id,
    )
    if post_check["blocked"]:
        return jsonify({
            "escalated": True,
            "reason": "Agent exceeded scope -- LLM explanation was inconsistent with the flagged "
                      "status. Escalated for human review instead of shown.",
            "watchdog_flags": post_check["flags"],
            "risk_score": risk_score,
            "flagged": flagged,
        }), 200

    # Step 8: de-tokenize -- the REAL account reference is restored only
    # here, at final response time, never sent to the LLM.
    return jsonify({
        "escalated": False,
        "live_call": True,
        "transaction_id": txn_id,
        "account_reference": ref_token,
        "real_account_id": record["account_id"],  # restored for the analyst's screen only
        "risk_score": risk_score,
        "flagged": flagged,
        "signals": signals,
        "llm_explanation": llm_explanation,
        "retrieved_clauses": [
            {"doc_code": c["metadata"]["doc_code"], "clause": c["metadata"]["clause"], "heading": c["metadata"]["heading"]}
            for c in chunks
        ],
        "retrieval_confidence_ok": conf_ok,
        "watchdog_flags": pre_check["flags"] + post_check["flags"],
        "human_review_note": "Draft -- Pending Fraud Analyst Review. This is not a final determination.",
    })


@app.route("/api/fraud-transactions", methods=["GET"])
def fraud_transactions_list():
    """Lightweight listing for the GUI table -- no PII beyond what a
    fraud analyst's own case queue would show (this is an internal
    analyst tool, not a customer-facing one)."""
    limit = int(request.args.get("limit", 200))
    flagged_only = request.args.get("flagged_only", "false").lower() == "true"
    rows = _fraud_records
    if flagged_only:
        rows = [r for r in rows if r.get("flagged")]
    rows = rows[:limit]
    return jsonify({
        "total": len(_fraud_records),
        "flagged_total": sum(1 for r in _fraud_records if r.get("flagged")),
        "returned": len(rows),
        "transactions": rows,
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
