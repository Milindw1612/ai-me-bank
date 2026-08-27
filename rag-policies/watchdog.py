# -*- coding: utf-8 -*-
"""
Watchdog / Guardrail Agent -- runs on every request, local, no LLM call
needed for its checks. A lightweight local extension of the same
governance philosophy as the site's Watchdog Council (governance-
supervisor.html): visibility and blocking authority over malformed
requests, not decision-making authority over the actual eligibility
or policy answer.

Checks:
  1. Outgoing-prompt PII re-scan -- broader/different patterns than
     pii_tokenizer.py's primary layer, as defense-in-depth (Scenario 1).
  2. Retrieval-confidence check -- flags weak grounding instead of
     letting the LLM answer from it.
  3. Rule/LLM consistency check (Loan only) -- verifies the LLM's
     explanation doesn't contradict the deterministic verdict
     (Scenario 2).
  4. Local audit log -- every request/response + every flag raised,
     tokens still masked, never raw PII.
"""
import json
import re
import time

AUDIT_LOG_PATH = "audit_log.jsonl"

# Broader re-scan patterns than the primary tokenizer -- deliberately
# more permissive on separators, so an Aadhaar written with hyphens or
# no separator at all (which slips past pii_tokenizer.py's stricter,
# space-only AADHAAR pattern) still gets caught here.
WATCHDOG_PII_PATTERNS = {
    "AADHAAR_LOOSE": re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    "PAN_LOOSE": re.compile(r"\b[A-Za-z]{5}\d{4}[A-Za-z]\b"),
    "PHONE_LOOSE": re.compile(r"\b(?:\+?91)?[6-9]\d{9}\b"),
    "EMAIL_LOOSE": re.compile(r"\b[\w.+-]+@[\w-]+\.\w+\b"),
}

RETRIEVAL_CONFIDENCE_THRESHOLD = 0.015  # RRF score below this = weak grounding

# Words that, if present in the LLM's explanation, would contradict a
# "Not Eligible" verdict -- signals the LLM softened/second-guessed a
# rejection instead of just explaining it (Scenario 2).
OVERRIDE_SIGNAL_PHRASES = [
    "could still be considered", "may still qualify", "recommend approving anyway",
    "should be approved", "is still eligible", "override the rejection",
    "despite this, eligible", "can proceed with the loan",
    # Calibrated against an observed real drift case: the LLM kept the
    # "Not Eligible" headline but wrapped it in enough encouragement/
    # reassurance that it functionally undermines the rejection --
    # scope creep from "explain the verdict" into "reassure the applicant."
    "silver lining", "excellent position", "very strong position",
    "favorable review", "we would be absolutely delighted", "achievable goal",
    "really positive news", "strong position to qualify",
]


def rescan_outgoing_prompt(prompt: str):
    """Layer 2 PII check, right before the LLM call. Returns a list of
    (label, matched_text) hits. Any hit should BLOCK the call."""
    hits = []
    for label, pattern in WATCHDOG_PII_PATTERNS.items():
        for m in pattern.finditer(prompt):
            hits.append((label, m.group(0)))
    return hits


def check_retrieval_confidence(retrieved_chunks):
    if not retrieved_chunks:
        return False, "No chunks retrieved."
    top_score = retrieved_chunks[0]["rrf_score"]
    if top_score < RETRIEVAL_CONFIDENCE_THRESHOLD:
        return False, f"Top retrieval RRF score {top_score:.4f} below confidence threshold {RETRIEVAL_CONFIDENCE_THRESHOLD}."
    return True, None


def check_rule_llm_consistency(rule_verdict: str, llm_explanation: str):
    """Loan GUI only. Returns (ok, reason)."""
    lowered = llm_explanation.lower()
    if rule_verdict == "Not Eligible":
        for phrase in OVERRIDE_SIGNAL_PHRASES:
            if phrase in lowered:
                return False, f"LLM explanation contains override-signal phrase '{phrase}' contradicting a Not Eligible verdict."
    return True, None


def log_event(event: dict):
    event["_ts"] = time.time()
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_watchdog(*, stage, prompt=None, retrieved_chunks=None, rule_verdict=None, llm_explanation=None, request_id=None):
    """Runs whichever checks are applicable and returns
    {"blocked": bool, "flags": [...]}"""
    flags = []
    blocked = False

    if prompt is not None:
        pii_hits = rescan_outgoing_prompt(prompt)
        if pii_hits:
            blocked = True
            flags.append({
                "check": "outgoing_prompt_pii_rescan",
                "result": "FAIL",
                "detail": f"{len(pii_hits)} PII pattern(s) detected in outgoing prompt: "
                          f"{[label for label, _ in pii_hits]}",
            })

    if retrieved_chunks is not None:
        ok, reason = check_retrieval_confidence(retrieved_chunks)
        if not ok:
            flags.append({"check": "retrieval_confidence", "result": "FAIL", "detail": reason})

    if rule_verdict is not None and llm_explanation is not None:
        ok, reason = check_rule_llm_consistency(rule_verdict, llm_explanation)
        if not ok:
            blocked = True
            flags.append({"check": "rule_llm_consistency", "result": "FAIL", "detail": reason})

    result = {"blocked": blocked, "flags": flags, "stage": stage, "request_id": request_id}
    log_event(result)
    return result


if __name__ == "__main__":
    # Scenario 1: PII that slipped past the primary tokenizer
    prompt_with_leak = "Applicant query: My Aadhaar number is 1234-5678-9012 and I want to know the maximum loan tenure."
    r1 = run_watchdog(stage="pre_llm_call", prompt=prompt_with_leak, request_id="demo-scenario-1")
    print("=== Scenario 1: PII leak re-scan ===")
    print(json.dumps(r1, indent=2))

    # Scenario 2: LLM explanation contradicts a Not Eligible verdict
    drifted_explanation = (
        "While the CIBIL score is below the standard threshold, given the applicant's strong income "
        "profile, this could still be considered for approval under exceptional circumstances."
    )
    r2 = run_watchdog(stage="post_llm_call", rule_verdict="Not Eligible", llm_explanation=drifted_explanation,
                       request_id="demo-scenario-2")
    print("\n=== Scenario 2: Rule/LLM consistency check ===")
    print(json.dumps(r2, indent=2))

    # A clean, non-flagged request for contrast
    r3 = run_watchdog(stage="post_llm_call", rule_verdict="Eligible",
                       llm_explanation="The applicant meets all standard eligibility criteria under LOAN_001 and LOAN_002.",
                       request_id="demo-clean-case")
    print("\n=== Clean case (no flags expected) ===")
    print(json.dumps(r3, indent=2))
