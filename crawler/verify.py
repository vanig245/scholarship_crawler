from datetime import date, timedelta
import config
from crawler.extract import norm, parse_amount

ELIGIBILITY_FIELDS = ["income_criteria", "age_criteria", "gender_criteria", "category_criteria",
                      "academic_requirements", "course_level", "domicile", "institution_requirements"]

def quote_in_page(quote, text):
    if quote.startswith(("[metadata]", "[link]")):
        return True            
    return norm(quote) in norm(text)

def validate_fields(rec, text):
    """Anti-hallucination gate: drop any field whose evidence quote cannot be found on the page."""
    rec["fields"] = {k: v for k, v in rec["fields"].items() if quote_in_page(v["quote"], text)}
    return rec

def score(rec, cls, page, apply_ok, today=None):
    today = today or date.today()
    F, parts = rec["fields"], []

    def add(name, pts, mx, why):
        parts.append({"check": name, "points": round(pts, 2), "max": mx, "reason": why})

    add("Official source", 25 * cls["trust"], 25,
        f"{cls['source_type']} domain {cls['domain']} (trust factor {cls['trust']})")
    present = page["ok"] and "name" in F
    add("Present on official source", 10 if present else 0, 10,
        "page fetched (HTTP 200) and scholarship name found" if present else "name not found on page")
    if "application_url" not in F:
        add("Application URL", 0, 10, "no application link found on page")
    elif apply_ok:
        add("Application URL", 10, 10, "application link found and responds")
    elif apply_ok is None:
        add("Application URL", 4, 10, "link found but could not be checked (robots)")
    else:
        add("Application URL", 0, 10, "application link found but did not respond")
    n = sum(1 for f in ELIGIBILITY_FIELDS if f in F)
    add("Eligibility evidence", 20 * min(1, n / 4), 20, f"{n}/4 eligibility fields supported by quoted evidence")

    cd = F.get("closing_date")
    if cd and cd["value"] == "ROLLING":
        add("Deadline evidence", 15, 20, "open-ended / rolling intake stated on page")
    elif cd:
        add("Deadline evidence", 20, 20, "deadline quoted from page")
    else:
        add("Deadline evidence", 0, 20, "no deadline found on page")

    fresh = bool(cd) and (cd["value"] == "ROLLING" or cd["value"] >= today.isoformat())
    add("Information current", 5 if fresh else 0, 5, "deadline is in the future / rolling" if fresh else "deadline passed or unknown")
    add("No conflicting dates", 0 if rec["conflict"] else 5, 5,
        f"multiple different deadlines on page: {rec['all_deadlines']}" if rec["conflict"] else "single consistent deadline")

    checks = [5 <= len(F["name"]["value"]) <= 150]
    if cd and cd["value"] != "ROLLING":
        checks.append(f"{today.year-3}" <= cd["value"][:4] <= f"{today.year+2}")
    if "amount" in F:
        a = parse_amount(F["amount"]["value"])
        checks.append(a is not None and a > 0)
    add("Extraction consistency", 5 * sum(checks) / len(checks), 5, f"{sum(checks)}/{len(checks)} extracted values pass validation")

    total = round(sum(p["points"] for p in parts), 1)
    gates_ok = cls["is_official"] == 1 and cd is not None and not rec["conflict"] and present
    label = "VERIFIED" if (total >= config.VERIFIED_THRESHOLD and gates_ok) else "REVIEW REQUIRED"
    return total, parts, label