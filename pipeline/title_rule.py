"""Title rule: is a posting an entry-level financial / credit analyst role?

A title is in role when it matches an INCLUDE pattern and no EXCLUDE pattern.
Exclusions win, so "Senior Credit Analyst" and "Credit Analyst, Sales" are out.
"""
import re

INCLUDE = re.compile(
    r"\b("
    r"financial analyst|finance analyst|credit analyst|credit underwriter|"
    r"underwriting analyst|underwriter|fp&a|"
    r"risk analyst|portfolio analyst|"
    r"investment banking analyst|investment banking associate analyst|"
    r"real estate finance|real estate analyst|"
    r"(commercial|corporate|abl|asset[- ]based lending)( banking)? analyst|"
    r"private equity analyst|private credit analyst|m&a analyst|"
    r"(private equity|m&a|investment banking|credit|risk|portfolio|finance|financial|"
    r"fp&a|treasury|lending) (analyst|associate)"
    r")\b",
    re.IGNORECASE,
)

EXCLUDE = re.compile(
    r"\b("
    r"senior|sr\.?|principal|director|vp|vice president|svp|avp|"
    r"managing director|head|lead|manager|"
    r"financial advisor|financial representative|relationship manager|"
    r"sales|business development"
    r")\b",
    re.IGNORECASE,
)


def in_role(title):
    title = title or ""
    return bool(INCLUDE.search(title)) and not EXCLUDE.search(title)
