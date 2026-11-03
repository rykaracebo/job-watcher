import pytest

from pipeline.title_rule import in_role


@pytest.mark.parametrize("title", [
    "Financial Analyst",
    "Credit Analyst I",
    "Credit Underwriter",
    "Underwriting Analyst - Commercial Real Estate",
    "FP&A Analyst",
    "Finance Analyst, Corporate Treasury",
    "Risk Analyst",
    "Portfolio Analyst",
    "Investment Banking Analyst",
    "Real Estate Finance Analyst",
    "ABL Analyst",
    "Commercial Banking Analyst",
    "Private Equity Analyst",
    "M&A Analyst",
    "credit analyst",
])
def test_in_role_titles(title):
    assert in_role(title)


@pytest.mark.parametrize("title", [
    "Senior Financial Analyst",
    "Sr. Credit Analyst",
    "Principal Risk Analyst",
    "Director, FP&A",
    "VP, Credit Underwriting",
    "Vice President - Investment Banking",
    "Managing Director, M&A",
    "Head of Credit Risk",
    "Lead Underwriter",
    "Credit Manager",
    "Financial Advisor",
    "Financial Representative",
    "Relationship Manager",
    "Sales Analyst",
    "Business Development Analyst",
    "Software Engineer",
    "Roving Personal Banker",
    "",
    None,
])
def test_out_of_role_titles(title):
    assert not in_role(title)


def test_exclusion_beats_inclusion():
    assert not in_role("Senior Credit Analyst")
    assert not in_role("Financial Analyst, Sales")


# ---- Titles added to the rule (real titles from the boards) ----

@pytest.mark.parametrize("title", [
    "Analyst, Risk",                                          # word order
    "Analyst, Alternative Investments Shareholder Reporting",
    "Analyst, Investment Banking - HG Debt Capital Markets",
    "Associate Analyst, Alternative Investments",             # associate analyst + function
    "Finance Reporting Analyst",
    "Enterprise Valuation Analyst II",
    "Valuation Analyst",
    "Global Technology Financial Planning & Analysis - Analyst",
    "Financial Planning and Analysis Analyst",
    "FP&A",
    "Credit Officer I",                                       # entry level only
    "GCIB- Commercial Credit Underwriter I/Commercial Credit Officer I",
    "2027 Commercial Real Estate Full-Time Analyst Program - Real Estate Banking (Dallas or Houston)",
    "2027 Global Finance & Business Management Analyst Program - Full Time Analyst",
    "2027 - Global Investment Banking Analyst Program - Full-Time - London",
])
def test_added_titles_are_in_role(title):
    assert in_role(title)


# ---- Titles the rule now leaves out ----

@pytest.mark.parametrize("title", [
    "Credit Officer II",                                      # not entry level
    "Credit Officer III",
    "Investment Banking Associate",                           # post-MBA title
    "Investment Banking Associate | Southern Region Coverage - Dallas",
    "M&A Associate (Tech) - SCIB",
    "Associate",
    "Associate Analyst",                                      # no finance function
    "Loan Documentation and Processing Intermediate Associate Analyst",
    "Intern - Credit Analyst",
    "Intern - Credit Risk Analyst",
    "Summer Analyst, Investment Banking",
    "2027 Commercial & Investment Bank Risk Management Summer Analyst Program",
    "2027 Corporate Analyst Development Program - Summer Analyst (Columbus)",
    "2027 Corporate & Investment Bank - Global Investment Banking Analyst Program - Off-Cycle Internship - Paris",
    "Co-op Financial Analyst",
    "Mortgage Loan Officer",
    "2027 Operations Analyst Program - Summer Analyst",
    "WM Operations Analyst Program - Fresh Graduates Hiring",
    "Analyst - Investment and Monetary Controls",             # dash is not word order
    "Consultant Relations Investment Analyst",                # client-facing
    "Analyst, Software Engineering",
])
def test_excluded_titles_are_out(title):
    assert not in_role(title)


# ---- Nothing sales-flavored may get in through the new word-order rule ----

FUNCTIONS = ["Risk", "Credit", "Finance", "Financial", "Investment Banking", "Alternative Investments",
             "Portfolio", "Treasury", "Lending", "Real Estate", "Valuation", "Private Equity", "M&A"]
SALES_TERMS = ["Sales", "Relationship Manager", "Financial Advisor", "Business Development",
               "Financial Representative", "Relationship", "Client"]


@pytest.mark.parametrize("function", FUNCTIONS)
@pytest.mark.parametrize("sales", SALES_TERMS)
def test_sales_terms_never_slip_through_word_order(function, sales):
    for title in (f"Analyst, {function} {sales}", f"Analyst, {sales} {function}",
                  f"{sales} Analyst, {function}", f"Analyst, {function} - {sales}",
                  f"{function} {sales} Analyst", f"Associate Analyst, {function} ({sales})"):
        assert not in_role(title), title


@pytest.mark.parametrize("function", FUNCTIONS)
def test_every_function_works_in_both_word_orders(function):
    assert in_role(f"Analyst, {function}")
    assert in_role(f"{function} Analyst")
