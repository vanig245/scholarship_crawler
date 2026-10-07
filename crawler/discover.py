import re
from ddgs import DDGS
import config, db
from crawler import fetch
from crawler.classify import classify_url
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode
import time

SKIP_EXT = re.compile(r"\.(pdf|jpe?g|png|gif|zip|docx?|xlsx?|pptx?)(\?|$)", re.I)
KEYWORD = re.compile(r"scholar|fellowship|stipend|yojana|scheme|bursary|grant", re.I)

from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

TRACKING = ("utm_", "fbclid", "gclid", "ref", "source")

def normalize(url):
    url = url.split("#")[0].strip()
    if not url.startswith("http") or SKIP_EXT.search(url):
        return None
    p = urlparse(url)
    q = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith(TRACKING)]
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme, p.netloc.lower(), path, "", urlencode(q), ""))

SKIP_LINK = re.compile(r"pfms|rti-act|/rti\b|tender|annual-report|screen-reader|login|sitemap|"
                       r"contact|feedback|archive|ResourcesHindi", re.I)

def search(query, n=8):
    for _ in range(2):
        try:
            hrefs = [r["href"] for r in DDGS().text(query, region="in-en", max_results=n) if r.get("href")]
            time.sleep(2)
            return hrefs
        except Exception as e:
            print(f"  search retry ({query[:40]}...): {e}")
            time.sleep(4)
    return []

def expansion_links(page, base_cls, limit=10):
    """Scholarship-looking links on a hub/listing page, to be crawled one level deeper."""
    out = []
    for href, text in page["links"]:
        url = normalize(href)
        if not url or SKIP_LINK.search(url) or url in out:
            continue
        cls = classify_url(url)
        if cls["source_type"] == "AGGREGATOR" or not KEYWORD.search(url + " " + text):
            continue
        if cls["domain"] == base_cls["domain"] or cls["is_official"]:
            out.append(url)
        if len(out) >= limit:
            break
    return out

def discover(conn):
    """Seeds + web search find candidate pages. Aggregators and official hub pages are only
    used to find links to OFFICIAL pages; aggregator content is never stored as a record."""
    seed_c, search_c, link_c, hubs = {}, {}, {}, {}

    def register(url, via):
        url = normalize(url)
        if not url:
            return None
        cls = classify_url(url)
        conn.execute("INSERT OR IGNORE INTO sources(url,domain,source_type,is_official,discovered_via,first_seen) "
                     "VALUES (?,?,?,?,?,?)", (url, cls["domain"], cls["source_type"], cls["is_official"], via, db.now()))
        return url, cls

    for s in config.SEEDS:
        r = register(s, "seed")
        if r:
            hubs[r[0]] = r[1]
            if r[1]["source_type"] != "AGGREGATOR":
                seed_c[r[0]] = "seed"

    for q in config.QUERIES:
        print(f"  searching: {q}")
        for u in search(q):
            r = register(u, "search")
            if not r:
                continue
            if r[1]["source_type"] == "AGGREGATOR":
                hubs[r[0]] = r[1]
            else:
                search_c.setdefault(r[0], "search")

    for hub_url, hub_cls in list(hubs.items())[:config.MAX_HUBS]:
        page = fetch.fetch(hub_url)
        if not page["ok"]:
            continue
        n = 0
        for href, text in page["links"]:
            r = register(href, "link")
            if not r or r[1]["source_type"] == "AGGREGATOR":
                continue
            l_url, l_cls = r
            blob = href + " " + text
            if hub_cls["source_type"] == "AGGREGATOR":
                ok = (l_cls["is_official"] or "official" in text.lower()) and \
                     (KEYWORD.search(blob) or "official" in text.lower())
            else:
                ok = KEYWORD.search(blob) and (l_cls["domain"] == hub_cls["domain"] or l_cls["is_official"])
            if ok:
                link_c.setdefault(l_url, "aggregator-outlink" if hub_cls["source_type"] == "AGGREGATOR" else "link-expansion")
                n += 1
                if n >= config.MAX_LINKS_PER_HUB:
                    break
    conn.commit()
    merged = {}
    for d in (seed_c, search_c, link_c):
        for k, v in d.items():
            merged.setdefault(k, v)
    return dict(list(merged.items())[:config.MAX_CANDIDATES])