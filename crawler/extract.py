import re
from datetime import date
from dateutil import parser as dparser

def norm(s):
    return re.sub(r"\s+", " ", s or "").strip().lower()

MONTHS = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
DATE_RE = re.compile(
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?[\s\-/.,]+{MONTHS}[a-z]*[\s\-/.,]+\d{{4}}\b"
    rf"|\b{MONTHS}[a-z]*\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}\b"
    r"|\b\d{1,2}[/\-.]\d{1,2}[/\-.]\d{4}\b", re.I)

AMOUNT_RE = re.compile(
    r"(?:(?:₹|Rs\.?|INR)\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:lakhs?|crores?|thousand))?"
    r"|\d+(?:\.\d+)?\s?(?:lakhs?|crores?))"
    r"(?:\s?(?:per|/|a)\s?(?:annum|year|month|semester|yr))?", re.I)

DEADLINE_KW = re.compile(r"last date|closing date|close date|deadline|due date|last day|"
                         r"applications?\s+(?:close|closes|closing|end|ends)|"
                         r"(?:apply|application|submission|registration)[^.]{0,40}(?:before|by|till|until|upto|up to)", re.I)
OPEN_KW = re.compile(r"opening date|start date|starting date|open from|"
                     r"applications?\s+(?:open|opens|begin|begins|start|starts|commence)", re.I)
ROLLING_RE = re.compile(r"throughout the year|round the year|all year round|rolling basis|open all year", re.I)
NAME_BLOCK = re.compile(r"\bportal\b|\bnodal\b|\bofficers?\b|\bhome\b|\blist of\b|\bsanctioned\b", re.I)
NAME_KW = re.compile(r"scholar|fellowship|stipend|award|scheme|yojana|grant|bursary|prize", re.I)
PROVIDER_RE = re.compile(r"(?:offered|provided|launched|funded|awarded|implemented|organi[sz]ed|administered|managed|sponsored)"
                         r"\s+by\s+(?:the\s+)?([A-Z][A-Za-z&.,'()\- ]{3,90}?)(?:\.|,|;|\sfor\s|\sto\s|\swith\s|$)")

ELIG_CUE = re.compile(r"should|must|shall|eligible|eligibility|only|required|criteria|not exceed|"
                      r"not more than|at least|minimum|maximum|open to|restricted to|reserved|limit", re.I)
CUE_FIELDS = {"income_criteria", "age_criteria", "gender_criteria", "category_criteria",
              "academic_requirements", "course_level", "domicile", "institution_requirements"}

def is_listing_page(text):
    """Pages that list many schemes (portals, indexes) are hubs, not single scholarships."""
    items = [l for l in text.split("\n")
             if 15 <= len(l) <= 140 and re.search(r"scholarship|fellowship|scheme|yojana", l, re.I)
             and not l.rstrip().endswith(".")]
    return len(items) >= 12
# field -> (must-match regex, optional second regex that must also match)
RULES = {
    "income_criteria": (r"income", r"lakh|₹|rs\.?\s?\d|inr|\d{5,}"),
    "age_criteria": (r"\bage\b|years of age|\baged\b|years old", r"\d{2}"),
    "gender_criteria": (r"\b(?:girls?|female|women|woman|boys?|male)\b", None),
    "category_criteria": (r"(?-i:\b(?:SC|ST|OBC|EWS|PwD|PWD|BPL)\b)|\b(?:minorit(?:y|ies)|divyang|disabilit(?:y|ies)|"
                          r"scheduled castes?|scheduled tribes?|backward class(?:es)?|general category|defence|ex-servicem[ae]n)\b", None),
    "academic_requirements": (r"\d{2}(?:\.\d+)?\s?%|percent|\bmarks\b|\bcgpa\b|\bgpa\b|merit|minimum .{0,20}(?:pass|score)", None),
    "course_level": (r"\bclass (?:9|10|11|12|xi|xii)\b|\b(?:10th|12th|undergraduate|postgraduate|graduation|b\.?\s?tech|m\.?\s?tech|"
                     r"mbbs|ph\.?\s?d|diploma|polytechnic|iti)\b", None),
    "domicile": (r"domicile|resident of|residing in|permanent resident|citizen of india|indian national|indian citizen", None),
    "institution_requirements": (r"recogni[sz]ed|affiliated|approved by|\bAICTE\b|\bUGC\b|\bNAAC\b|\bNIRF\b", None),
    "documents_required": (r"documents? (?:required|needed)|income certificate|caste certificate|mark ?sheet|aadhaar|aadhar|"
                           r"bank (?:account|passbook)|photograph", None),
    "selection_process": (r"selection|shortlist|merit list|interview|selected on", None),
    "renewal_requirements": (r"\brenew", None),
}

def sentences(text):
    out = []
    for line in text.split("\n"):
        for s in re.split(r"(?<=[.;!?])\s+", line):
            s = s.strip()
            if len(s) >= 12:
                out.append(s[:500])
    return out

def units(text):
    """Sentences plus (short line + next line) pairs, to catch table rows like 'Last date' | '31-08-2026'."""
    lines = text.split("\n")
    pairs = [lines[i] + " " + lines[i + 1] for i in range(len(lines) - 1) if len(lines[i]) < 80]
    return sentences(text) + pairs

def find_dates(s):
    out = []
    for m in DATE_RE.finditer(s):
        raw = re.sub(r"(\d)(?:st|nd|rd|th)\b", r"\1", m.group(0), flags=re.I)
        try:
            out.append((dparser.parse(raw, dayfirst=True).date().isoformat(), m.group(0)))
        except (ValueError, OverflowError):
            continue
    return out

def parse_amount(s):
    m = AMOUNT_RE.search(s or "")
    if not m:
        return None
    t = m.group(0).lower()
    num = re.search(r"\d[\d,]*(?:\.\d+)?", t)
    if not num:
        return None
    v = float(num.group(0).replace(",", ""))
    if "crore" in t: v *= 1e7
    elif "lakh" in t: v *= 1e5
    elif "thousand" in t: v *= 1e3
    return int(v)

def is_scholarship_page(text):
    t = text.lower()
    return (len(text) > 800 and len(re.findall(r"scholarship|fellowship", t)) >= 3
            and "eligib" in t and bool(re.search(r"\bapply\b|application", t)))

def _first(us, must, also=None):
    for u in us:
        if re.search(must, u, re.I) and (also is None or re.search(also, u, re.I)):
            return u
    return None

def extract(page):
    text, us = page["text"], units(page["text"])
    F = {}

    # name
    for cand in (page["h1"], re.split(r"\s[|–—-]\s", page["title"])[0] if page["title"] else ""):
        cand = (cand or "").strip()
        if 5 <= len(cand) <= 150 and NAME_KW.search(cand) and not NAME_BLOCK.search(cand):
            in_text = norm(cand) in norm(text)
            F["name"] = {"value": cand, "quote": cand if in_text else f"[metadata] {cand}"}
            break
    if "name" not in F:
        return None

    # provider
    for s in sentences(text):
        m = PROVIDER_RE.search(s)
        if m:
            F["provider"] = {"value": m.group(1).strip(" ,."), "quote": s}
            break
    if "provider" not in F:
        sn = page["site_name"] or (re.split(r"\s[|–—-]\s", page["title"])[-1] if page["title"] else "")
        if sn:
            F["provider"] = {"value": sn.strip(), "quote": f"[metadata] {sn.strip()}"}

    # amount
    for u in us:
        if AMOUNT_RE.search(u) and re.search(r"scholarship|stipend|amount|assistance|per annum|per month|award|fellowship|grant|worth|up to|tuition", u, re.I) \
                and not re.search(r"income", u, re.I):
            F["amount"] = {"value": AMOUNT_RE.search(u).group(0).strip(), "quote": u}
            break

    # dates
    deadlines = []
    for u in us:
        if DEADLINE_KW.search(u):
            deadlines += [(iso, u) for iso, _ in find_dates(u)]
    rolling_q = _first(sentences(text), ROLLING_RE.pattern)
    distinct = sorted({d for d, _ in deadlines})
    if distinct:
        latest = distinct[-1]
        q = next(u for d, u in deadlines if d == latest)
        F["closing_date"] = {"value": latest, "quote": q}
    elif rolling_q:
        F["closing_date"] = {"value": "ROLLING", "quote": rolling_q}
    for u in us:
        if OPEN_KW.search(u) and find_dates(u):
            F["opening_date"] = {"value": find_dates(u)[0][0], "quote": u}
            break

    # eligibility-type fields
    for f, (must, also) in RULES.items():
        q = next((u for u in us
                  if re.search(must, u, re.I) and (also is None or re.search(also, u, re.I))
                  and (f not in CUE_FIELDS or (len(u) >= 40 and ELIG_CUE.search(u)))), None)
        if q:
            F[f] = {"value": q, "quote": q}

    # application link (taken from the page's own anchors, so it can't be invented)
    best = None
    for href, label in page["links"]:
        if re.search(r"\bapply\b|application|register|registration", label, re.I) and not href.startswith(("mailto", "javascript")):
            best = best or (href, label)
    if best:
        F["application_url"] = {"value": best[0], "quote": f"[link] {best[1]} -> {best[0]}"}

    # structured, machine-readable eligibility derived ONLY from the quoted sentences
    S = {}
    if "income_criteria" in F:
        S["income_max_inr"] = parse_amount(F["income_criteria"]["quote"])
    if "age_criteria" in F:
        m = re.search(r"(?:below|under|not exceed(?:ing)?|up to|maximum|less than|not more than)\D{0,25}(\d{2})", F["age_criteria"]["quote"], re.I)
        S["age_max"] = int(m.group(1)) if m else None
    if "academic_requirements" in F:
        m = re.search(r"(\d{2}(?:\.\d+)?)\s?%", F["academic_requirements"]["quote"])
        S["min_percentage"] = float(m.group(1)) if m else None
    if "category_criteria" in F:
        found = re.findall(r"(?-i:\b(?:SC|ST|OBC|EWS|PwD|PWD|BPL)\b)|minorit(?:y|ies)|divyang", F["category_criteria"]["quote"], re.I)
        S["categories_mentioned"] = sorted(set(x.upper() for x in found))
    if "gender_criteria" in F:
        S["gender_mentioned"] = sorted(set(x.lower() for x in re.findall(r"girls?|female|women|woman|boys?|male", F["gender_criteria"]["quote"], re.I)))

    return {"fields": F, "structured": S, "all_deadlines": distinct,
            "conflict": len(distinct) > 1, "rolling": F.get("closing_date", {}).get("value") == "ROLLING"}