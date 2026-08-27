# -*- coding: utf-8 -*-
"""
Generates 13 synthetic internal policy PDFs for the local Hybrid RAG demo
(Loan/Credit, HR, and General document collections). All content is
fabricated for demonstration purposes -- these are NOT real bank policies.

Run: python generate_policy_pdfs.py
Output: loan/*.pdf, hr/*.pdf, general/*.pdf
"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_CENTER

styles = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=4, textColor=colors.HexColor("#4A1420"))
SUB = ParagraphStyle("Sub", parent=styles["Normal"], fontSize=9, textColor=colors.HexColor("#64748B"), spaceAfter=14)
H2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12.5, spaceBefore=14, spaceAfter=6, textColor=colors.HexColor("#D97706"))
BODY = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10, leading=14, spaceAfter=6)
NOTE = ParagraphStyle("Note", parent=styles["Normal"], fontSize=9, leading=13, textColor=colors.HexColor("#475569"),
                       backColor=colors.HexColor("#F1F5F9"), borderPadding=8, spaceAfter=10, spaceBefore=6)
FOOTER = ParagraphStyle("Footer", parent=styles["Normal"], fontSize=7.5, textColor=colors.HexColor("#94A3B8"),
                         alignment=TA_CENTER)

TABLE_STYLE = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4A1420")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
])


def bullets(items):
    # Plain "- " prefix instead of ReportLab's bullet glyph: the bullet
    # character does not extract cleanly via pdfplumber (renders as a
    # "(cid:127)" artifact in retrieved text), which would look broken
    # if raw retrieved chunks are shown on screen during a walkthrough.
    return [Paragraph(f"- {t}", BODY) for t in items]


def build_pdf(path, doc_code, title, sections):
    doc = SimpleDocTemplate(path, pagesize=A4,
                             leftMargin=2.2 * cm, rightMargin=2.2 * cm,
                             topMargin=2 * cm, bottomMargin=2 * cm)
    story = [
        Paragraph("AI-ME BANK  -  INTERNAL POLICY DOCUMENT", SUB),
        Paragraph(title, H1),
        Paragraph(f"Document Code: {doc_code} &nbsp;|&nbsp; Version: 3.2 &nbsp;|&nbsp; "
                  f"Effective Date: 01-Apr-2026 &nbsp;|&nbsp; Status: Active", SUB),
    ]
    for heading, body in sections:
        story.append(Paragraph(heading, H2))
        if isinstance(body, list):
            story.extend(bullets(body))
        elif isinstance(body, Table):
            story.append(body)
            story.append(Spacer(1, 6))
        else:
            story.append(Paragraph(body, BODY))
    story.append(Spacer(1, 18))
    story.append(Paragraph(
        "ILLUSTRATIVE / SYNTHETIC DOCUMENT  -  for local Hybrid RAG demonstration purposes only. "
        "Not a real regulatory filing or actual bank policy.", FOOTER))
    doc.build(story)
    print(f"  Created: {path}")


def make_table(header, rows):
    data = [header] + rows
    return Table(data, style=TABLE_STYLE, hAlign="LEFT")


# ============================================================= LOAN =============================================================

def loan_001():
    sections = [
        ("1. Applicant Age Requirements",
         "Applicants must be between 21 and 60 years of age at the time of application, and must not exceed "
         "65 years of age at loan maturity. For co-applicants, at least one applicant must satisfy this criterion."),
        ("2. Employment Eligibility", [
            "Salaried applicants: minimum 1 year with the current employer, and minimum 2 years total work experience.",
            "Self-employed applicants: minimum 3 years of continuous business vintage under the same registration.",
            "Applicants on probation with their current employer are not eligible until confirmation.",
        ]),
        ("3. Minimum Income Requirements", make_table(
            ["Applicant Category", "Minimum Monthly / Annual Income"],
            [
                ["Salaried (Metro)", "Rs. 25,000 net monthly income"],
                ["Salaried (Non-Metro)", "Rs. 18,000 net monthly income"],
                ["Self-Employed", "Rs. 4,00,000 net annual profit (per latest ITR)"],
                ["Pensioner", "Rs. 15,000 monthly pension"],
            ]
        )),
        ("4. Credit Score Requirements", make_table(
            ["CIBIL Score Band", "Eligibility Track"],
            [
                ["750 and above", "Standard track  -  auto-eligible, subject to FOIR and documentation"],
                ["700 - 749", "Standard track with standard pricing (see LOAN_005 for pricing linkage)"],
                ["650 - 699", "Conditional  -  requires DSCR/FOIR headroom per LOAN_002, manual review"],
                ["Below 650", "Not eligible for personal loan under this policy"],
            ]
        )),
        ("5. Required Documents",
         "Refer to LOAN_004_Documentation_Policy for the complete document checklist by applicant category. "
         "Applications missing mandatory documents move to Pending Documentation status."),
        ("6. Decision Categories", [
            "Eligible  -  all criteria satisfied within standard thresholds.",
            "Needs Manual Review  -  one or more criteria fall within a conditional/exception band.",
            "Not Eligible  -  a hard criterion (age, employment, minimum CIBIL) is not satisfied.",
        ]),
    ]
    build_pdf("loan/LOAN_001_Personal_Loan_Eligibility_Policy.pdf", "LOAN-001",
              "Personal Loan Eligibility Policy", sections)


def loan_002():
    sections = [
        ("1. FOIR Definition and Formula",
         "Fixed Obligation to Income Ratio (FOIR) measures an applicant's total fixed monthly financial obligations "
         "(including the proposed EMI) as a percentage of net monthly income:<br/><br/>"
         "<b>FOIR (%) = (Total Existing EMIs + Credit Card Minimum Due + Proposed EMI) ÷ Net Monthly Income × 100</b>"),
        ("2. Maximum FOIR by Applicant Category", make_table(
            ["Applicant Category", "Maximum Permitted FOIR"],
            [
                ["Salaried", "50%"],
                ["Self-Employed", "45%"],
                ["Pensioner", "40%"],
            ]
        )),
        ("3. Existing Obligation Rules", [
            "All active EMIs reflected in the applicant's credit bureau report must be included, regardless of lender.",
            "Credit card obligations are counted at 5% of the outstanding statement balance, per card.",
            "Obligations where the applicant is a co-signer/guarantor are included at 50% weight unless the "
            "primary borrower's repayment track record is fully current for 24 months.",
        ]),
        ("4. FOIR Calculation Example",
         "<b>Example:</b> Net monthly income Rs. 60,000. Existing car loan EMI Rs. 8,000. Credit card outstanding "
         "Rs. 40,000 (5% = Rs. 2,000). Proposed personal loan EMI Rs. 12,000.<br/>"
         "FOIR = (Rs. 8,000 + Rs. 2,000 + Rs. 12,000) ÷ Rs. 60,000 × 100 = <b>36.7%</b>  -  within the 50% salaried threshold."),
        ("5. Exception Handling",
         "Applications exceeding the maximum FOIR by up to 5 percentage points may proceed to Manual Review if "
         "supported by a co-applicant with independent income, or additional collateral cover of at least 25% "
         "of the loan amount. FOIR breaches beyond 5 percentage points above threshold are Not Eligible under "
         "this policy without Risk Committee override."),
    ]
    build_pdf("loan/LOAN_002_FOIR_and_Income_Policy.pdf", "LOAN-002",
              "FOIR and Income Policy", sections)


def loan_003():
    sections = [
        ("1. Minimum and Maximum Loan Amounts",
         "Personal loans under this policy range from a minimum of <b>Rs. 50,000</b> to a maximum of "
         "<b>Rs. 25,00,000</b>, subject to income, FOIR, and credit score criteria in LOAN_001 and LOAN_002."),
        ("2. Permitted Loan Tenure",
         "Standard tenure range is <b>12 to 60 months</b>. Minimum EMI under any tenure combination must not be "
         "less than Rs. 1,500."),
        ("3. Credit-Score-Based Tenure Limits", make_table(
            ["CIBIL Score Band", "Maximum Permitted Tenure"],
            [
                ["750 and above", "60 months"],
                ["700 - 749", "48 months"],
                ["650 - 699", "36 months"],
            ]
        )),
        ("4. High-Value Loan Review Requirements",
         "Any application for a loan amount exceeding <b>Rs. 10,00,000</b> requires review and sign-off by a "
         "Regional Credit Manager regardless of credit score or FOIR standing, in addition to the standard "
         "decisioning workflow. Amounts exceeding Rs. 20,00,000 additionally require Zonal Credit Head sign-off."),
    ]
    build_pdf("loan/LOAN_003_Loan_Amount_and_Tenure_Policy.pdf", "LOAN-003",
              "Loan Amount and Tenure Policy", sections)


def loan_004():
    sections = [
        ("1. Salaried Applicant Documents", [
            "PAN card and Aadhaar card",
            "Last 3 months' salary slips",
            "Last 6 months' primary bank account statement",
            "Form 16 or latest year's ITR acknowledgement",
            "Employment ID card or offer/appointment letter (for employment tenure verification)",
        ]),
        ("2. Self-Employed Applicant Documents", [
            "PAN card and Aadhaar card",
            "Last 2 years' ITR with computation of income",
            "Last 12 months' primary business bank account statement",
            "GST registration certificate and last 4 quarters' GSTR-3B filings",
            "Business registration / establishment proof (Udyam/Shop Act/GST certificate)",
        ]),
        ("3. Missing-Document Handling",
         "If an application is missing one or more mandatory documents at submission, it is moved to "
         "<b>Pending Documentation</b> status. The applicant is notified and given a 15-calendar-day window "
         "to submit the outstanding documents."),
        ("4. Pending Documentation Status",
         "Applications remaining in Pending Documentation status beyond <b>30 calendar days</b> from the "
         "original submission date are automatically closed as Not Eligible  -  Incomplete Documentation, and "
         "the applicant must reapply if they wish to proceed."),
    ]
    build_pdf("loan/LOAN_004_Documentation_Policy.pdf", "LOAN-004",
              "Documentation Policy", sections)


def loan_005():
    sections = [
        ("1. Automatic Eligibility Rules",
         "An application is auto-approved on the standard track when ALL of the following hold simultaneously: "
         "age and employment criteria met (LOAN_001), CIBIL score 700 or above, FOIR within the category maximum "
         "(LOAN_002), loan amount and tenure within the credit-score-based limits (LOAN_003), and all mandatory "
         "documents received (LOAN_004)."),
        ("2. Manual-Review Triggers", [
            "CIBIL score between 650 and 699 (conditional band)",
            "FOIR exceeding the category maximum by up to 5 percentage points",
            "Loan amount exceeding Rs. 10,00,000 (high-value review, per LOAN_003)",
            "Self-employed applicant with 2-3 years business vintage (borderline tenure)",
            "Any discrepancy flagged between declared income and bureau/bank-statement data",
        ]),
        ("3. Not-Eligible Conditions", [
            "CIBIL score below 650",
            "FOIR exceeding the category maximum by more than 5 percentage points",
            "Applicant age outside the 21-60 (application) / 65 (maturity) window",
            "Mandatory documentation not received within 30 days (Pending Documentation lapse)",
        ]),
        ("4. Decision Classification",
         "Every application resolves to exactly one of three classifications: <b>Eligible</b> (auto-approved), "
         "<b>Needs Manual Review</b> (routed to a credit officer with the specific trigger reason attached), or "
         "<b>Not Eligible</b> (declined, with the specific policy clause cited to the applicant)."),
    ]
    build_pdf("loan/LOAN_005_Credit_Decision_Rules.pdf", "LOAN-005",
              "Credit Decision Rules", sections)


# =============================================================== HR ===============================================================

def hr_001():
    sections = [
        ("1. Annual Leave",
         "Confirmed employees are entitled to <b>18 days</b> of annual leave per calendar year, credited in full "
         "at the start of the year. New joiners accrue leave on a pro-rated monthly basis (1.5 days/month)."),
        ("2. Sick Leave",
         "Employees are entitled to <b>12 days</b> of sick leave per calendar year. A medical certificate is "
         "required for any sick leave exceeding 2 consecutive working days."),
        ("3. Carry-Forward Rules",
         "A maximum of <b>15 days</b> of unused annual leave may be carried forward into the following calendar "
         "year. Any balance beyond 15 days lapses on 31 December and is not encashed, except where local labour "
         "law mandates encashment."),
        ("4. Leave Approval Requirements", [
            "Leave of 3 consecutive working days or fewer: reporting manager approval only.",
            "Leave exceeding 3 consecutive working days: reporting manager AND HR Business Partner approval.",
            "Leave requests should be submitted at least 3 working days in advance except for medical emergencies.",
        ]),
    ]
    build_pdf("hr/HR_001_Leave_Policy.pdf", "HR-001", "Leave Policy", sections)


def hr_002():
    sections = [
        ("1. Maximum WFH Days",
         "Eligible employees may work from home for up to <b>8 days per calendar month</b>. Extended WFH beyond "
         "this limit requires department-head approval and is granted only in exceptional circumstances."),
        ("2. Manager Approval",
         "All WFH days must be requested and approved by the reporting manager at least 24 hours in advance, "
         "except in documented emergencies (illness, family emergency, transit disruption)."),
        ("3. Business Requirements",
         "Roles that are customer-facing, branch-based, or require physical presence for operational reasons "
         "(e.g., cash handling, in-branch customer service) are not eligible for regular WFH arrangements."),
        ("4. Security Requirements for Remote Work", [
            "Company VPN is mandatory for accessing any internal system while working remotely.",
            "Use of personal USB drives or unapproved external storage devices is prohibited.",
            "Workstations must auto-lock after 5 minutes of inactivity.",
            "Customer or account data must never be downloaded to a personal (non-company-issued) device.",
        ]),
    ]
    build_pdf("hr/HR_002_Work_From_Home_Policy.pdf", "HR-002", "Work From Home Policy", sections)


def hr_003():
    sections = [
        ("1. Hotel Reimbursement Limits", make_table(
            ["City Category", "Maximum Reimbursement (per night)"],
            [
                ["Metro (Mumbai, Delhi, Bengaluru, Chennai, Kolkata, Hyderabad)", "Rs. 6,000"],
                ["Non-Metro", "Rs. 4,000"],
            ]
        )),
        ("2. Meal Allowances",
         "A per-diem meal allowance of <b>Rs. 1,200/day</b> applies for domestic business travel, inclusive of all "
         "meals. International travel allowances are set separately per destination and require prior Finance "
         "approval."),
        ("3. Expense-Claim Deadlines",
         "All travel expense claims must be submitted within <b>15 calendar days</b> of trip completion. Claims "
         "submitted after 30 days require additional Finance approval and a documented reason for the delay."),
        ("4. Receipt Requirements",
         "Original receipts are mandatory for any single expense line above <b>Rs. 500</b>. Expenses below Rs. 500 may "
         "be self-declared, subject to a monthly aggregate self-declaration cap of Rs. 2,000."),
    ]
    build_pdf("hr/HR_003_Travel_and_Expense_Policy.pdf", "HR-003", "Travel and Expense Policy", sections)


def hr_004():
    sections = [
        ("1. Promotion Eligibility",
         "An employee becomes eligible for promotion consideration upon achieving a rating of at least "
         "\"Meets Expectations\" in each of the last <b>2 performance review cycles</b>."),
        ("2. Minimum Time in Role",
         "A minimum of <b>18 months</b> in the current grade is required before promotion consideration, "
         "measured from the date of the last promotion or date of joining, whichever is later."),
        ("3. Performance Requirements for Accelerated Promotion",
         "Employees rated \"Exceeds Expectations\" or higher in both of the last 2 cycles may be considered for "
         "accelerated promotion before completing 18 months in role, subject to VP-level approval."),
        ("4. Disciplinary-Action Restrictions",
         "Any employee with an active disciplinary action recorded within the last <b>12 months</b> is not "
         "eligible for promotion consideration in the current cycle, regardless of performance rating."),
        ("5. Approval Process",
         "Promotion nominations follow: (1) Manager nomination with written justification → (2) Skip-level "
         "manager review → (3) HR calibration committee review across the function → (4) Final approval by "
         "the function head."),
    ]
    build_pdf("hr/HR_004_Performance_and_Promotion_Policy.pdf", "HR-004",
              "Performance and Promotion Policy", sections)


def hr_005():
    sections = [
        ("1. Working Hours",
         "Standard working hours are <b>9:30 AM to 6:30 PM</b>, Monday to Friday, with a 1-hour lunch break, "
         "inclusive of 8 core productive hours per day."),
        ("2. Daily Working-Hour Requirement",
         "Employees are required to log a minimum of <b>8 productive hours</b> per working day via the "
         "attendance system, exclusive of the lunch break."),
        ("3. Late-Arrival Rules", [
            "Arrival more than 15 minutes after the standard start time is recorded as a late arrival.",
            "3 late arrivals in a calendar month result in an informal advisory from the reporting manager.",
            "More than 5 late arrivals in a calendar month result in a formal written warning via HR.",
        ]),
        ("4. Attendance Review",
         "Reporting managers review attendance records monthly. HR conducts an independent attendance audit "
         "on a quarterly basis across all departments."),
    ]
    build_pdf("hr/HR_005_Attendance_and_Working_Hours_Policy.pdf", "HR-005",
              "Attendance and Working Hours Policy", sections)


# ============================================================ GENERAL ============================================================

def general_001():
    sections = [
        ("1. Company Overview",
         "Ai-ME BANK is a technology-forward banking institution committed to responsible innovation, "
         "regulatory compliance, and customer trust. This handbook applies to all employees, contractors, "
         "and vendors with access to company systems."),
        ("2. Employee Responsibilities",
         "Every employee is responsible for adhering to all applicable company policies, completing mandatory "
         "compliance training on schedule, and promptly reporting any known or suspected policy violation to "
         "their manager or the Ethics & Compliance desk."),
        ("3. Information Protection",
         "Customer and employee data must be handled strictly on a need-to-know basis. Sharing customer "
         "information outside authorized business purposes, even internally, is a policy violation regardless "
         "of intent."),
        ("4. Professional Conduct",
         "Ai-ME BANK maintains a workplace free of harassment and discrimination of any kind. Employees must "
         "disclose any actual or potential conflict of interest (financial, familial, or business) to their "
         "manager and the Ethics & Compliance desk."),
        ("5. Responsible Use of Company Systems",
         "Company systems, devices, and network access are provided for business use. Usage may be monitored "
         "in line with applicable law. Installation of unauthorized software, including unsanctioned AI/chatbot "
         "tools, on company systems is prohibited."),
    ]
    build_pdf("general/GENERAL_001_Company_Handbook.pdf", "GENERAL-001", "Company Handbook", sections)


def general_002():
    sections = [
        ("1. Password Protection",
         "Passwords must be a minimum of <b>12 characters</b>, rotated every <b>90 days</b>, and must not reuse "
         "any of the last 5 passwords. Multi-factor authentication (MFA) is mandatory for all access to company "
         "systems, without exception."),
        ("2. Confidential Information Classification", make_table(
            ["Classification", "Handling Requirement"],
            [
                ["Public", "No restriction on distribution"],
                ["Internal", "Company employees/contractors only"],
                ["Confidential", "Named individuals with a specific business need"],
                ["Restricted", "Named individuals + InfoSec approval + audit logging"],
            ]
        )),
        ("3. Personal-Device Restrictions",
         "Customer or account data must never be stored on a personal device. Personal devices may access "
         "company email only via an approved, MDM-enrolled configuration issued by IT."),
        ("4. Approved Services",
         "Only IT-approved cloud and SaaS services may be used for company business. Use of unsanctioned "
         "public AI/chatbot tools with any customer, employee, or confidential company data is strictly "
         "prohibited under this policy."),
        ("5. Security-Incident Reporting",
         "Any suspected security incident (lost device, phishing attempt, suspected unauthorized access) must "
         "be reported to the InfoSec team within <b>1 hour</b> of discovery. Employees must not attempt to "
         "independently investigate or remediate a suspected breach."),
    ]
    build_pdf("general/GENERAL_002_Information_Security_Policy.pdf", "GENERAL-002",
              "Information Security Policy", sections)


def general_003():
    sections = [
        ("1. Purchase Approval Thresholds", make_table(
            ["Purchase Value", "Required Approval"],
            [
                ["Below Rs. 25,000", "Department Head"],
                ["Rs. 25,000 - Rs. 2,00,000", "Department Head + Finance"],
                ["Above Rs. 2,00,000", "Senior Management (CFO) + Finance"],
            ]
        )),
        ("2. Department Approval",
         "Every purchase requires sign-off from the budget owner confirming the spend is within the approved "
         "departmental budget for the current fiscal year."),
        ("3. Finance Approval",
         "A Purchase Order (PO) must be issued by Finance before any commitment is made to a vendor for "
         "purchases above Rs. 25,000. Verbal or email-only commitments without a PO are not authorized."),
        ("4. Senior-Management Approval",
         "CFO (or CEO, for multi-year contracts) sign-off is mandatory for any single purchase exceeding "
         "Rs. 2,00,000, and for any contractual commitment spanning more than one fiscal year regardless of value."),
        ("5. Prevention of Purchase Splitting",
         "Splitting a single procurement requirement into multiple smaller purchase orders to stay below an "
         "approval threshold is strictly prohibited and is subject to internal audit review and disciplinary "
         "action."),
    ]
    build_pdf("general/GENERAL_003_Procurement_Policy.pdf", "GENERAL-003", "Procurement Policy", sections)


# ============================================================= FRAUD =============================================================

def fraud_001():
    sections = [
        ("1. Amount-Spike Threshold",
         "A transaction is flagged for amount-spike review when its value exceeds the account's trailing "
         "average transaction amount by the following multiples:"),
        ("1.1 Amount-Spike Bands", make_table(
            ["Ratio vs. Account Average", "Signal Weight"],
            [
                ["2.5x - 4x", "Low (+18 points)"],
                ["4x - 8x", "Medium (+35 points)"],
                ["8x and above", "High (+55 points)"],
            ]
        )),
        ("2. Velocity Limits",
         "More than 5 transactions from a single account within any rolling 60-minute window, or more than "
         "15 within a rolling 24-hour window, triggers a velocity flag regardless of individual transaction size."),
        ("3. New-Device + High-Amount Combination Rule",
         "A transaction from a device not previously associated with the account, combined with an amount "
         "exceeding 3x the account's trailing average, adds +30 points to the transaction's risk score -- "
         "this combination is treated as materially higher risk than either signal alone."),
        ("4. Odd-Hour Transaction Flagging",
         "Transactions initiated between 1:00 AM and 4:00 AM local time add +20 points to the risk score when "
         "combined with any other active signal. An odd-hour transaction with no other signal present is not, "
         "by itself, sufficient grounds for review."),
        ("5. Channel Risk Weighting", make_table(
            ["Channel", "Baseline Risk Weighting"],
            [
                ["UPI", "Standard"],
                ["IMPS", "Standard"],
                ["NEFT", "Standard"],
                ["Card - Card Not Present", "Elevated (+10 points)"],
            ]
        )),
    ]
    build_pdf("fraud/FRAUD_001_Transaction_Monitoring_Thresholds_Policy.pdf", "FRAUD-001",
              "Transaction Monitoring Thresholds Policy", sections)


def fraud_002():
    sections = [
        ("1. Sanctions and PEP Watchlist Screening",
         "Every beneficiary and counterparty is screened against the current sanctions list and Politically "
         "Exposed Persons (PEP) register before a transaction clears. A positive match blocks the transaction "
         "pending manual Compliance review -- this is a hard stop, not a scoring signal."),
        ("2. High-Risk Merchant Category List",
         "Transactions to merchants on the High-Risk Merchant Category List add +40 points to the transaction's "
         "risk score. The list is reviewed and republished quarterly by the Fraud & AML desk."),
        ("2.1 Current High-Risk Categories", [
            "Unlicensed/offshore forex remittance services",
            "Unregistered crypto-asset exchanges",
            "Unverified peer-to-peer marketplace sellers",
            "Short-term/payday lending platforms not on the approved partner list",
        ]),
        ("3. Cross-Border and Geo-Mismatch Escalation",
         "A transaction originating from an IP location outside the customer's registered home country adds "
         "+40 points to the risk score. If the origin country is on the Enhanced Monitoring Jurisdictions list, "
         "the transaction is additionally routed for mandatory Level-2 review regardless of total score."),
        ("4. Beneficiary Risk Scoring",
         "A beneficiary account that has itself been flagged in 3 or more prior confirmed-fraud cases in the "
         "preceding 12 months is treated as a high-risk beneficiary -- any transaction to that beneficiary adds "
         "+25 points, independent of the sending account's own history."),
    ]
    build_pdf("fraud/FRAUD_002_AML_and_Watchlist_Screening_Policy.pdf", "FRAUD-002",
              "AML and Watchlist Screening Policy", sections)


def fraud_003():
    sections = [
        ("1. Risk Score Bands",
         "Every transaction receives a composite risk score from 0-100, built from the signals in FRAUD_001 "
         "and FRAUD_002. The score determines the automated action taken:"),
        ("1.1 Action Bands", make_table(
            ["Risk Score", "Automated Action"],
            [
                ["0 - 44", "Clear -- no action, transaction proceeds normally"],
                ["45 - 74", "Flagged -- routed to Fraud Analyst for review, transaction proceeds"],
                ["75 - 100", "Auto-Freeze -- transaction held pending analyst confirmation"],
            ]
        )),
        ("2. CRO-Approved Auto-Freeze Threshold",
         "The 75-point auto-freeze threshold in section 1.1 is a Chief Risk Officer-approved setting and may "
         "only be changed with CRO sign-off and a documented rationale. It may not be adjusted by any "
         "individual analyst or by the Fraud Detection system itself."),
        ("3. Customer Appeal Rights",
         "Any customer whose transaction is auto-frozen must be notified within 2 hours and given a documented "
         "channel to contest the freeze. An unresolved appeal older than 24 hours is automatically escalated "
         "to Level-2 review under FRAUD_004."),
        ("4. No Fully Autonomous Confirmation",
         "Regardless of risk score, the system never independently confirms a transaction as fraudulent. "
         "Auto-Freeze is a precautionary hold, not a fraud determination -- only a human Fraud Analyst or the "
         "Fraud Risk Committee (per FRAUD_004) may classify a case as confirmed fraud."),
    ]
    build_pdf("fraud/FRAUD_003_Auto_Action_Thresholds_Policy.pdf", "FRAUD-003",
              "Auto-Action Thresholds Policy", sections)


def fraud_004():
    sections = [
        ("1. Analyst Review SLA",
         "A Flagged transaction (risk score 45-74) must receive first analyst review within 4 business hours. "
         "An Auto-Freeze transaction (risk score 75+) must receive first analyst review within 1 hour, given "
         "the customer impact of a held transaction."),
        ("2. Escalation Ladder", make_table(
            ["Level", "Trigger", "Owner"],
            [
                ["Level 1", "Standard flagged/frozen review", "Fraud Analyst"],
                ["Level 2", "Analyst cannot reach a determination within SLA, or customer appeal unresolved 24h+", "Senior Fraud Analyst"],
                ["Level 3", "Cross-border high-risk-jurisdiction match, or case value above Rs. 5,00,000", "Fraud Risk Committee"],
            ]
        )),
        ("3. Customer Notification and Appeal Rights",
         "Every auto-frozen transaction triggers a customer notification within 2 hours (SMS/app notification), "
         "stating the transaction is under review and providing an appeal channel. Silence from the customer "
         "is never treated as an admission -- an unresolved case still follows the standard investigation timeline."),
        ("4. Provisional Credit Rules",
         "Where a confirmed-fraud determination is reached and the customer bears no fault (e.g., unauthorized "
         "third-party transaction), provisional credit is issued within 10 business days of confirmation, "
         "pending final reconciliation."),
    ]
    build_pdf("fraud/FRAUD_004_Case_Investigation_and_Escalation_Policy.pdf", "FRAUD-004",
              "Case Investigation and Escalation Policy", sections)


def fraud_005():
    sections = [
        ("1. Case Closure Classifications",
         "Every investigated case must be closed under exactly one of the following classifications: "
         "Confirmed Fraud, False Positive (legitimate transaction, no action needed), or Inconclusive "
         "(insufficient evidence -- held open for 30 days pending further activity, then closed by default "
         "to False Positive with a documented note)."),
        ("2. Mandatory Audit Trail Fields", [
            "Risk score and every signal that contributed to it, at time of flagging",
            "Every analyst and system action taken on the case, with timestamp and actor",
            "The specific policy clause(s) relied on for the final classification",
            "Customer notification and appeal correspondence, if any",
        ]),
        ("3. Retention Period",
         "Confirmed Fraud case records are retained for 8 years. False Positive and Inconclusive case records "
         "are retained for 5 years. All retention periods run from the case closure date, not the transaction date."),
        ("4. Regulatory Reporting Threshold",
         "Any case classified as Confirmed Fraud involving a transaction value above Rs. 10,00,000, or any case "
         "with a cross-border high-risk-jurisdiction match regardless of value, must be reported to the "
         "designated regulatory desk within the statutory reporting window."),
    ]
    build_pdf("fraud/FRAUD_005_Case_Closure_and_Audit_Policy.pdf", "FRAUD-005",
              "Case Closure and Audit Policy", sections)


def main():
    os.makedirs("loan", exist_ok=True)
    os.makedirs("fraud", exist_ok=True)

    print("Generating LOAN documents...")
    loan_001(); loan_002(); loan_003(); loan_004(); loan_005()
    print("Generating FRAUD documents...")
    fraud_001(); fraud_002(); fraud_003(); fraud_004(); fraud_005()
    print("\nDone. 10 PDFs generated across loan/, fraud/.")


if __name__ == "__main__":
    main()
