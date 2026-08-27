# -*- coding: utf-8 -*-
"""
PII Tokenization Layer — the primary input guard.

Two modes:
  - Structured form (Loan GUI): schema-based. We KNOW which fields are
    identifying, so they are simply never serialized into any prompt.
    No detection needed — this is the more robust of the two paths.
  - Free text (Policy Assistant GUI): regex (PAN/Aadhaar/phone/email,
    fixed high-confidence formats) + spaCy NER (person/org names).
    Detected spans are replaced with placeholder tokens; the real
    values are held only in an in-memory map for this request, never
    written to disk or logs, and only ever substituted back in at the
    final response-rendering step.

NOTE: this module is deliberately the ONLY line of defense at the input
stage. The Watchdog (watchdog.py) re-scans the assembled prompt right
before the LLM call as a second, independent layer — see Scenario 1 in
the plan (an Aadhaar number without spacing is designed to slip past
the regex here, and get caught by the Watchdog's broader re-scan).
"""
import re

import spacy

_nlp = None


def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


# Fixed-format patterns -- deliberately strict/exact formats, so that an
# unusual variant (e.g. no spacing in an Aadhaar number) is a realistic,
# reproducible way to demonstrate the primary layer missing something
# (Scenario 1 relies on this).
PATTERNS = {
    "PAN": re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"),
    "AADHAAR": re.compile(r"\b\d{4}\s\d{4}\s\d{4}\b"),  # requires spacing -- see note above
    "PHONE": re.compile(r"\b(?:\+91[-\s]?)?[6-9]\d{9}\b"),
    "EMAIL": re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    "ACCOUNT_NO": re.compile(r"\b\d{9,18}\b"),  # bank account numbers, 9-18 digits
}

# Structured-form fields that are identifying and must NEVER be
# serialized into any prompt sent downstream, for the Loan GUI.
LOAN_FORM_PII_FIELDS = {"applicant_name", "pan", "aadhaar", "account_number", "phone", "email"}

# Domain acronyms/terms the small spaCy NER model sometimes misclassifies
# as PERSON/ORG (a false positive -- over-masking, not a security risk,
# but noisy in a live demo). Skipped so these plain policy terms aren't
# needlessly tokenized.
_NER_WHITELIST = {
    "pan", "aadhaar", "foir", "cibil", "emi", "gst", "gstr", "dscr", "itr",
    "pf", "esi", "hr", "it", "vpn", "mfa", "kyc", "aml", "cam", "hod", "cfo",
}


def strip_structured_pii(form_data: dict) -> dict:
    """Loan GUI path: returns only the non-identifying fields. The
    caller should never have access to the stripped fields again in
    this pipeline -- they are simply dropped, not tokenized, because
    nothing downstream needs them."""
    return {k: v for k, v in form_data.items() if k not in LOAN_FORM_PII_FIELDS}


def tokenize_free_text(text: str):
    """Policy Assistant GUI path. Returns (tokenized_text, token_map)
    where token_map maps placeholder -> original value, held in memory
    only by the caller for this single request."""
    token_map = {}
    counter = [0]

    def replace(match, label):
        counter[0] += 1
        placeholder = f"[PII_{label}_{counter[0]}]"
        token_map[placeholder] = match.group(0)
        return placeholder

    working = text
    for label, pattern in PATTERNS.items():
        working = pattern.sub(lambda m, l=label: replace(m, l), working)

    # NER pass for person/org names not caught by the regexes above
    doc = get_nlp()(working)
    # Process entities in reverse order so character offsets stay valid
    # as we splice the string.
    spans = [
        (ent.start_char, ent.end_char, ent.text) for ent in doc.ents
        if ent.label_ in ("PERSON", "ORG") and ent.text.lower().strip(".,") not in _NER_WHITELIST
    ]
    for start, end, ent_text in sorted(spans, key=lambda s: s[0], reverse=True):
        counter[0] += 1
        placeholder = f"[PII_NAME_{counter[0]}]"
        token_map[placeholder] = ent_text
        working = working[:start] + placeholder + working[end:]

    return working, token_map


def detokenize(text: str, token_map: dict) -> str:
    """Final response-rendering step only -- substitutes real values
    back in. Never call this before the LLM call; only after, on the
    response that goes back to the browser."""
    for placeholder, original in token_map.items():
        text = text.replace(placeholder, original)
    return text


if __name__ == "__main__":
    samples = [
        "My name is Rohit Sharma, my PAN is ABCDE1234F and my Aadhaar is 1234 5678 9012. "
        "Can I get a personal loan of Rs. 5,00,000?",
        "I am Priya from Acme Textiles, my account number is 123456789012, please check my FOIR.",
        # Scenario 1: Aadhaar with HYPHENS instead of spaces -- deliberately outside the
        # primary regex format (which only matches space-separated groups), and the
        # hyphens also break it out of the ACCOUNT_NO digit-run pattern.
        "My Aadhaar number is 1234-5678-9012 and I want to know the maximum loan tenure.",
    ]
    for s in samples:
        tokenized, tmap = tokenize_free_text(s)
        print("ORIGINAL :", s)
        print("TOKENIZED:", tokenized)
        print("TOKEN MAP:", tmap)
        print("ROUND-TRIP DETOKENIZED:", detokenize(tokenized, tmap))
        print()
