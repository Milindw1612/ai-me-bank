# -*- coding: utf-8 -*-
"""
Generates a small set of synthetic MSME loan applications for the
CAM Prep demo. All company names, financials, and identifiers are
fabricated -- no real applicant or business data is used.

Run: python generate_applications.py
Output: applications.json
"""
import json
import random

random.seed(7)

SECTORS = [
    "Textile Manufacturing", "Auto Components", "Food Processing",
    "IT Services", "Pharma Distribution", "Construction Materials",
    "Furniture Manufacturing", "Packaging", "Commercial Real Estate Leasing",
    "Electronics Assembly", "Logistics & Warehousing", "Agri-Processing",
]
WATCHLIST_SECTORS = {"Commercial Real Estate Leasing"}

CITIES = ["Mumbai", "Pune", "Ahmedabad", "Coimbatore", "Ludhiana", "Surat", "Indore", "Nashik"]

COMPANY_PREFIXES = ["Shree", "Om", "Sai", "Vardhman", "Krishna", "Suraj", "Vishal", "Anand", "Ganesh", "Star"]
COMPANY_SUFFIXES = ["Industries", "Enterprises", "Traders", "Manufacturing Co.", "Exports", "Textiles", "Engineering Works", "Agro Products"]


def make_financials(profile):
    """profile in {'strong', 'borderline', 'weak'}"""
    if profile == "strong":
        turnover = random.uniform(3.5, 12) * 1e7  # 3.5-12 Cr
        gst_divergence = random.uniform(0, 8)
        net_profit_margin = random.uniform(0.08, 0.15)
        dscr = random.uniform(1.5, 2.3)
        cibil = random.randint(750, 810)
        nwc_positive_years = 3
    elif profile == "borderline":
        turnover = random.uniform(1.5, 6) * 1e7
        gst_divergence = random.uniform(8, 20)
        net_profit_margin = random.uniform(0.03, 0.08)
        dscr = random.uniform(1.05, 1.4)
        cibil = random.randint(670, 730)
        nwc_positive_years = random.choice([2, 3])
    else:  # weak
        turnover = random.uniform(0.6, 3) * 1e7
        gst_divergence = random.uniform(18, 38)
        net_profit_margin = random.uniform(-0.02, 0.04)
        dscr = random.uniform(0.7, 1.1)
        cibil = random.randint(560, 660)
        nwc_positive_years = random.choice([0, 1])

    return {
        "annual_turnover_itr": round(turnover, -3),
        "annual_turnover_gst": round(turnover * (1 - gst_divergence / 100), -3),
        "gst_itr_divergence_pct": round(gst_divergence, 1),
        "net_profit_margin_pct": round(net_profit_margin * 100, 1),
        "dscr": round(dscr, 2),
        "cibil_score": cibil,
        "nwc_positive_years_last3": nwc_positive_years,
    }


def main():
    n = 18
    profiles = (["strong"] * 6) + (["borderline"] * 7) + (["weak"] * 5)
    random.shuffle(profiles)

    apps = []
    for i, profile in enumerate(profiles):
        sector = random.choice(SECTORS)
        vintage_years = random.randint(2, 18)
        requested_amount = round(random.uniform(15, 150) * 1e5, -4)  # 15L - 1.5Cr
        requested_tenure_years = random.choice([2, 3, 4, 5, 7])
        financials = make_financials(profile)

        apps.append({
            "application_id": f"MSME-{i+1:03d}",
            "company_name": f"{random.choice(COMPANY_PREFIXES)} {random.choice(COMPANY_SUFFIXES)}",
            "sector": sector,
            "on_watchlist": sector in WATCHLIST_SECTORS,
            "city": random.choice(CITIES),
            "business_vintage_years": vintage_years,
            "requested_amount": requested_amount,
            "requested_tenure_years": requested_tenure_years,
            "purpose": random.choice([
                "Working capital enhancement", "Machinery purchase",
                "Warehouse expansion", "Raw material procurement line",
                "Fleet/vehicle financing",
            ]),
            **financials,
            "_profile_seed": profile,  # internal only, for our own QA -- not shown in demo
        })

    with open("applications.json", "w", encoding="utf-8") as f:
        json.dump(apps, f, indent=2)

    print(f"Generated {len(apps)} synthetic MSME applications -> applications.json")
    from collections import Counter
    print("Profile mix:", Counter(a["_profile_seed"] for a in apps))


if __name__ == "__main__":
    main()
