# -*- coding: utf-8 -*-
"""
Deterministic Loan Eligibility Rule Engine -- pure Python, no LLM call.

Mirrors LOAN_001 (age/employment/CIBIL), LOAN_002 (FOIR), and LOAN_003
(amount/tenure) exactly. This is what actually decides Eligible /
Needs Manual Review / Not Eligible -- the LLM is only ever asked to
explain a verdict this module already produced.
"""

FOIR_MAX = {"salaried": 50, "self_employed": 45, "pensioner": 40}
TENURE_MAX_BY_CIBIL = [(750, 60), (700, 48), (650, 36)]


def evaluate(applicant: dict) -> dict:
    """
    applicant: {
        "age": int, "employment_type": "salaried"|"self_employed"|"pensioner",
        "years_current_employer": float, "years_total_experience": float,
        "business_vintage_years": float,  # for self-employed
        "cibil_score": int,
        "monthly_income": float,
        "existing_emis": float, "credit_card_outstanding": float,
        "requested_amount": float, "requested_tenure_months": int,
        "proposed_emi": float,
    }
    Returns: {"verdict": ..., "reasons": [...], "foir_pct": ..., ...}
    """
    reasons = []
    hard_fail = []
    conditional = []

    # --- Age ---
    age = applicant.get("age", 0)
    if not (21 <= age <= 60):
        hard_fail.append(f"Applicant age {age} is outside the permitted 21-60 window (LOAN_001 clause 1).")

    # --- Employment ---
    emp_type = applicant.get("employment_type", "salaried")
    if emp_type == "salaried":
        if applicant.get("years_current_employer", 0) < 1 or applicant.get("years_total_experience", 0) < 2:
            hard_fail.append("Salaried applicant does not meet minimum employer tenure / total experience (LOAN_001 clause 2).")
    elif emp_type == "self_employed":
        vintage = applicant.get("business_vintage_years", 0)
        if vintage < 2:
            hard_fail.append("Business vintage below 2 years (LOAN_001 clause 2).")
        elif vintage < 3:
            conditional.append(f"Business vintage {vintage} years is borderline (2-3 year band) (LOAN_001 clause 2).")

    # --- CIBIL ---
    cibil = applicant.get("cibil_score", 0)
    if cibil < 650:
        hard_fail.append(f"CIBIL score {cibil} is below the minimum 650 (LOAN_001 clause 4 / LOAN_005 clause 3).")
    elif cibil < 700:
        conditional.append(f"CIBIL score {cibil} falls in the conditional 650-699 band (LOAN_001 clause 4).")

    # --- FOIR ---
    income = max(applicant.get("monthly_income", 1), 1)
    cc_component = applicant.get("credit_card_outstanding", 0) * 0.05
    foir_pct = (applicant.get("existing_emis", 0) + cc_component + applicant.get("proposed_emi", 0)) / income * 100
    foir_max = FOIR_MAX.get(emp_type, 50)
    if foir_pct > foir_max + 5:
        hard_fail.append(f"FOIR {foir_pct:.1f}% exceeds the {foir_max}% {emp_type} maximum by more than 5pp (LOAN_002 clause 5).")
    elif foir_pct > foir_max:
        conditional.append(f"FOIR {foir_pct:.1f}% exceeds the {foir_max}% {emp_type} maximum (within 5pp exception band) (LOAN_002 clause 5).")

    # --- Amount / tenure ---
    amount = applicant.get("requested_amount", 0)
    tenure = applicant.get("requested_tenure_months", 0)
    if not (50000 <= amount <= 2500000):
        hard_fail.append(f"Requested amount Rs. {amount:,.0f} is outside the Rs. 50,000-25,00,000 range (LOAN_003 clause 1).")
    if amount > 1000000:
        conditional.append(f"Requested amount Rs. {amount:,.0f} exceeds Rs. 10,00,000 -- requires Regional Credit Manager review (LOAN_003 clause 4).")

    max_tenure = 24
    for min_cibil, t in TENURE_MAX_BY_CIBIL:
        if cibil >= min_cibil:
            max_tenure = t
            break
    if tenure > max_tenure:
        conditional.append(f"Requested tenure {tenure} months exceeds the {max_tenure}-month limit for CIBIL {cibil} (LOAN_003 clause 3).")

    if hard_fail:
        verdict = "Not Eligible"
        reasons = hard_fail
    elif conditional:
        verdict = "Needs Manual Review"
        reasons = conditional
    else:
        verdict = "Eligible"
        reasons = ["All criteria (age, employment, CIBIL, FOIR, amount, tenure) satisfied within standard thresholds."]

    return {
        "verdict": verdict,
        "reasons": reasons,
        "foir_pct": round(foir_pct, 1),
        "foir_max": foir_max,
        "max_tenure_months": max_tenure,
    }


if __name__ == "__main__":
    profiles = [
        ("Strong", {"age": 34, "employment_type": "salaried", "years_current_employer": 4,
                     "years_total_experience": 8, "cibil_score": 780, "monthly_income": 90000,
                     "existing_emis": 8000, "credit_card_outstanding": 20000, "proposed_emi": 12000,
                     "requested_amount": 500000, "requested_tenure_months": 48}),
        ("Borderline", {"age": 29, "employment_type": "salaried", "years_current_employer": 1.5,
                          "years_total_experience": 3, "cibil_score": 690, "monthly_income": 45000,
                          "existing_emis": 12000, "credit_card_outstanding": 30000, "proposed_emi": 10000,
                          "requested_amount": 400000, "requested_tenure_months": 36}),
        ("Weak (Scenario 2 case)", {"age": 26, "employment_type": "salaried", "years_current_employer": 2,
                                      "years_total_experience": 3, "cibil_score": 620, "monthly_income": 35000,
                                      "existing_emis": 8000, "credit_card_outstanding": 15000, "proposed_emi": 9000,
                                      "requested_amount": 300000, "requested_tenure_months": 36}),
    ]
    for label, p in profiles:
        result = evaluate(p)
        print(f"--- {label} ---")
        print(f"Verdict: {result['verdict']}  (FOIR: {result['foir_pct']}%, max {result['foir_max']}%)")
        for r in result["reasons"]:
            print("  -", r)
        print()
