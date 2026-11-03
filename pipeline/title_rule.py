"""Title rule: is a posting an entry-level financial / credit analyst role?

A title is in role when it matches an INCLUDE pattern and no EXCLUDE pattern.
Exclusions win, so "Senior Credit Analyst" and "Credit Analyst, Sales" are out.
"""
import re

# A finance function that can sit before "analyst" ("Risk Analyst") or after
# it ("Analyst, Risk"). Function words alone never make a title in role.
FUNCTION = (
    r"financial planning (?:and|&) analysis|fp&a|finance reporting|finance|financial|"
    r"credit|risk|portfolio|treasury|lending|real estate|valuation|underwriting|"
    r"investment banking|private equity|private credit|m&a|"
    r"alternative investments?|investments?"
)

INCLUDE = re.compile(
    r"\b("
    r"financial analyst|finance analyst|credit analyst|credit underwriter|"
    r"underwriting analyst|underwriter|fp&a|financial planning (and|&) analysis|"
    r"risk analyst|portfolio analyst|"
    r"investment banking analyst|investment banking associate analyst|"
    r"real estate finance|real estate analyst|"
    r"(commercial|corporate|abl|asset[- ]based lending)( banking)? analyst|"
    r"private equity analyst|private credit analyst|m&a analyst|"
    # "Credit Officer I" is entry level; II and above are not included.
    r"credit officer [i1]|"
    # Plain "associate" is left out of investment banking, private equity and
    # M&A: in those fields it is a post-MBA title.
    r"(credit|risk|portfolio|finance|financial|fp&a|treasury|lending) (analyst|associate)|"
    # Function before the title: "Valuation Analyst", "Finance Reporting Analyst",
    # "Financial Planning & Analysis - Analyst", "Associate Analyst" with a function.
    rf"({FUNCTION}) (associate )?analyst|"
    # Word order: "Analyst, Risk", "Analyst, Alternative Investments".
    rf"analyst\s*[,:]\s*({FUNCTION})|"
    # Full-time analyst programs in a finance function.
    rf"({FUNCTION}).{{0,60}}analyst program"
    r")\b",
    re.IGNORECASE,
)

EXCLUDE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|director|vp|vice president|svp|avp|"
    r"managing director|head|lead|manager|"
    r"financial advisor|financial representative|relationship manager|"
    r"sales|business development|relationship|relations|client|"
    r"intern|internship|summer|co-op"
    r")\b",
    re.IGNORECASE,
)


def in_role(title):
    title = title or ""
    return bool(INCLUDE.search(title)) and not EXCLUDE.search(title)
