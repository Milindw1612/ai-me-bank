"""Bureau & Tax Verification Agent — CIBIL, AA feeds, GSTR-1/3B."""
from a1_msme_credit.states import CreditState
from a1_msme_credit.tools import bureau_pull_score, gstr_fetch_returns, aa_fetch_bank_feed


async def run(state: CreditState) -> CreditState:
    bureau = await bureau_pull_score(state["applicant_token"])
    gstr = await gstr_fetch_returns(state["applicant_token"])
    aa_summary = await aa_fetch_bank_feed(state["applicant_token"])

    return {
        **state,
        "cibil_score": bureau["score"],
        "gstr_filed_ok": gstr.get("all_filed", False),
        "gstr_summary": gstr,
        "aa_bank_feed_summary": aa_summary,
        "bureau_tax_done": True,
        "current_step": "bureau_tax_verification",
    }
