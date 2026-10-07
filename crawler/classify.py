import re
from urllib.parse import urlparse
import config

def get_domain(url):
    d = (urlparse(url).netloc or "").lower()
    return d[4:] if d.startswith("www.") else d

def classify_url(url):
    d = get_domain(url)
    base = {"domain": d, "source_type": "UNKNOWN", "is_official": 0, "trust": 0.0}
    if any(d == a or d.endswith("." + a) for a in config.AGGREGATOR_DOMAINS):
        return {**base, "source_type": "AGGREGATOR"}
    for suffix, stype in config.OFFICIAL_SUFFIXES.items():
        if d.endswith(suffix):
            return {**base, "source_type": stype, "is_official": 1, "trust": 1.0}
    label = _label(d)
    if any(k in label for k in config.AGG_KEYWORDS):
        return {**base, "source_type": "AGGREGATOR"}
    if "csr" in label:
        return {**base, "source_type": "CORPORATE_CSR", "is_official": 1, "trust": 0.85}
    if any(k in label for k in ("foundation", "trust", "ngo")):
        return {**base, "source_type": "NGO_TRUST", "is_official": 1, "trust": 0.85}
    return base   # decided later from page content

def _label(domain):
    parts = domain.split(".")
    skip = {"co", "com", "org", "ac", "gov", "nic", "net", "edu", "in"}
    for p in reversed(parts):
        if p not in skip:
            return re.sub(r"[^a-z0-9]", "", p)
    return ""

def refine_source(cls, page):
    """Unknown domain counts as the provider's own site only if the page identifies itself as that organisation."""
    if cls["source_type"] != "UNKNOWN":
        return cls
    label = _label(cls["domain"])
    blob = re.sub(r"[^a-z0-9]", "", (page["title"] + page["site_name"]).lower())
    if len(label) >= 5 and label[:6] in blob:
        text = page["text"].lower()
        stype = "CORPORATE_CSR" if re.search(r"\bcsr\b|corporate social responsibility", text) \
            else "NGO_TRUST" if re.search(r"foundation|trust|society|ngo", blob + text[:3000]) \
            else "PROVIDER_SITE"
        return {**cls, "source_type": stype, "is_official": 1, "trust": 0.85}
    return cls