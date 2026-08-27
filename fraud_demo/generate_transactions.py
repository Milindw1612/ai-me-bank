# -*- coding: utf-8 -*-
"""
Generates a synthetic 10,000-record bank transaction dataset for the
Fraud Detection demo. All data is fabricated -- no real customer or
transaction data is used anywhere in this script or its output.

Run: python generate_transactions.py
Output: transactions.json (10,000 records)
"""
import json
import random
import datetime

random.seed(42)

N_TOTAL = 10000
N_ACCOUNTS = 2200
FRAUD_RATE = 0.026  # ~260 records get an injected fraud pattern

CHANNELS = ["UPI", "NEFT", "IMPS", "Card", "POS"]
CHANNEL_WEIGHTS = [0.42, 0.14, 0.18, 0.16, 0.10]

NORMAL_MERCHANTS = [
    "Local Kirana Store", "Reliance Retail", "Amazon India", "Flipkart",
    "Swiggy", "Zomato", "BSES Electricity Bill", "Airtel Recharge",
    "IRCTC", "BigBasket", "Apollo Pharmacy", "HDFC Credit Card Payment",
    "LIC Premium", "School Fee Payment", "Metro Card Recharge",
    "Petrol Pump - HP", "DMart", "Myntra", "Local Restaurant",
    "Rent Payment - Landlord", "Salary Credit - Employer", "Uber",
    "Ola", "Netflix India", "Housing Society Maintenance",
]
RISKY_MERCHANTS = [
    "Crypto Exchange - OffshoreX", "QuickCash Lending Ltd",
    "Unverified Marketplace Seller", "Forex Remit - Unlisted",
    "Gaming Wallet Topup - Unverified", "Shell Trading Co",
]

CITIES_IN = ["Mumbai", "Delhi", "Bengaluru", "Pune", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad"]
GEO_IN = "IN"
GEO_RISKY = ["NG", "RU", "KY", "VN", "PA"]  # unusual origin codes for injected geo-mismatch cases

# Fabricated customer identity fields -- these exist to make the source
# data look like a genuine bank record (a real transaction DB always has
# a name/address attached to an account). They are exactly the kind of
# identifying data the Input Guard must strip before anything reaches
# the LLM -- same treatment as account_id, just richer.
FIRST_NAMES = ["Anil", "Priya", "Rohit", "Sunita", "Vikram", "Neha", "Arjun", "Kavita",
               "Rajesh", "Meera", "Sanjay", "Pooja", "Amit", "Divya", "Karan", "Ritu",
               "Manoj", "Shalini", "Deepak", "Anjali"]
LAST_NAMES = ["Sharma", "Kumar", "Patel", "Reddy", "Iyer", "Singh", "Gupta", "Nair",
              "Rao", "Mehta", "Joshi", "Verma", "Desai", "Pillai", "Chatterjee", "Bose"]
AREAS = ["Andheri West", "Koramangala", "Banjara Hills", "Salt Lake", "Vasant Kunj",
         "Aundh", "Gachibowli", "Alwarpet", "Indiranagar", "Ballygunge", "Malviya Nagar",
         "Kothrud", "Jubilee Hills", "Powai", "HSR Layout"]
ACCOUNT_TYPES = ["Savings", "Current", "Salary", "NRI"]
ACCOUNT_TYPE_WEIGHTS = [0.55, 0.15, 0.25, 0.05]

START_DATE = datetime.datetime(2026, 5, 1)
DAYS_SPAN = 90


def make_accounts(n):
    accounts = []
    for i in range(n):
        acc_id = f"ACC{i+1:06d}"
        tenure_days = random.choice([random.randint(30, 365), random.randint(365, 2500)])
        # baseline spend behaviour per account
        base_amt = random.choice([
            random.uniform(200, 2000),      # low spenders
            random.uniform(2000, 15000),    # mid spenders
            random.uniform(15000, 80000),   # high spenders
        ])
        home_device = f"DEV-{random.randint(100000, 999999)}"
        home_city = random.choice(CITIES_IN)
        area = random.choice(AREAS)
        pincode = random.randint(100000, 899999)
        accounts.append({
            "account_id": acc_id,
            "tenure_days": tenure_days,
            "prior_avg_txn_amount": round(base_amt, 2),
            "home_device": home_device,
            "home_city": home_city,
            "customer_name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",
            "address": f"{area}, {home_city} - {pincode}",
            "account_type": random.choices(ACCOUNT_TYPES, weights=ACCOUNT_TYPE_WEIGHTS)[0],
        })
    return accounts


def random_timestamp():
    offset_days = random.uniform(0, DAYS_SPAN)
    ts = START_DATE + datetime.timedelta(days=offset_days)
    return ts


def gen_normal_transaction(txn_id, acc):
    ts = random_timestamp()
    # normal transactions cluster around waking hours
    hour = random.choice([random.randint(7, 22), random.randint(7, 22), random.randint(0, 23)])
    ts = ts.replace(hour=hour, minute=random.randint(0, 59))
    amount = max(50, random.gauss(acc["prior_avg_txn_amount"], acc["prior_avg_txn_amount"] * 0.35))
    return {
        "transaction_id": txn_id,
        "account_id": acc["account_id"],
        "customer_name": acc["customer_name"],
        "address": acc["address"],
        "account_type": acc["account_type"],
        "timestamp": ts.isoformat(),
        "amount": round(amount, 2),
        "channel": random.choices(CHANNELS, weights=CHANNEL_WEIGHTS)[0],
        "merchant": random.choice(NORMAL_MERCHANTS),
        "device_id": acc["home_device"],
        "ip_country": GEO_IN,
        "ip_city": acc["home_city"],
        "customer_tenure_days": acc["tenure_days"],
        "prior_avg_txn_amount": acc["prior_avg_txn_amount"],
        "injected_fraud_pattern": None,
    }


def gen_fraud_transaction(txn_id, acc):
    ts = random_timestamp()
    pattern = random.choice([
        "amount_spike", "new_device_high_amount", "odd_hour_high_amount",
        "geo_mismatch", "risky_merchant",
    ])

    base = gen_normal_transaction(txn_id, acc)
    base["injected_fraud_pattern"] = pattern

    if pattern == "amount_spike":
        base["amount"] = round(acc["prior_avg_txn_amount"] * random.uniform(6, 22), 2)

    elif pattern == "new_device_high_amount":
        base["device_id"] = f"DEV-{random.randint(100000, 999999)}"
        base["amount"] = round(acc["prior_avg_txn_amount"] * random.uniform(3, 9), 2)

    elif pattern == "odd_hour_high_amount":
        ts = ts.replace(hour=random.randint(1, 4), minute=random.randint(0, 59))
        base["timestamp"] = ts.isoformat()
        base["amount"] = round(acc["prior_avg_txn_amount"] * random.uniform(2.5, 7), 2)

    elif pattern == "geo_mismatch":
        base["ip_country"] = random.choice(GEO_RISKY)
        base["ip_city"] = "Unknown"
        base["amount"] = round(acc["prior_avg_txn_amount"] * random.uniform(1.5, 5), 2)

    elif pattern == "risky_merchant":
        base["merchant"] = random.choice(RISKY_MERCHANTS)
        base["amount"] = round(acc["prior_avg_txn_amount"] * random.uniform(2, 6), 2)

    return base


def main():
    accounts = make_accounts(N_ACCOUNTS)
    n_fraud = int(N_TOTAL * FRAUD_RATE)
    n_normal = N_TOTAL - n_fraud

    records = []
    for i in range(n_normal):
        acc = random.choice(accounts)
        records.append(gen_normal_transaction(f"TXN{i+1:06d}", acc))
    for i in range(n_fraud):
        acc = random.choice(accounts)
        records.append(gen_fraud_transaction(f"TXN{n_normal+i+1:06d}", acc))

    random.shuffle(records)
    # re-sequence transaction_id after shuffle so IDs still look sequential/realistic
    for idx, r in enumerate(records):
        r["transaction_id"] = f"TXN{idx+1:06d}"

    out_path = "transactions.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=None, separators=(",", ":"))

    print(f"Generated {len(records)} records -> {out_path}")
    print(f"  Injected fraud-pattern records: {n_fraud} ({n_fraud/len(records)*100:.2f}%)")
    print(f"  Clean records: {n_normal}")


if __name__ == "__main__":
    main()
