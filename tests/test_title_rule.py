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
