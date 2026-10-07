import json
from datetime import date, datetime, timedelta
import config, db
from crawler import discover, fetch, extract, verify
from crawler.classify import classify_url, refine_source

FIELDS = ["name", "provider", "application_url", "amount", "academic_requirements", "course_level",
          "income_criteria", "age_criteria", "gender_criteria", "category_criteria", "domicile",
          "institution_requirements", "opening_date", "closing_date", "documents_required",
          "selection_process", "renewal_requirements"]
TRACKED = ["name", "amount", "application_url", "opening_date", "closing_date", "income_criteria",
           "age_criteria", "gender_criteria", "category_criteria", "course_level", "documents_required"]

def compute_status(rec):
    cd = rec["fields"].get("closing_date")
    if not cd:
        return "REVIEW_REQUIRED"
    if cd["value"] == "ROLLING":
        return "ACTIVE"
    d = date.fromisoformat(cd["value"])
    if d < date.today():
        return "EXPIRED"
    return "EXPIRING_SOON" if (d - date.today()).days <= config.SOON_DAYS else "ACTIVE"

def log_change(conn, sid, field, old, new, url, quote):
    conn.execute("INSERT INTO change_log(scholarship_id,field,old_value,new_value,detected_at,source_url,evidence_quote) "
                 "VALUES (?,?,?,?,?,?,?)", (sid, field, str(old), str(new), db.now(), url, quote))
    print(f"  CHANGE DETECTED  {field}: {old}  ->  {new}")

def mark_unverifiable(conn, sid, url, reason, permanent, stats):
    row = conn.execute("SELECT status FROM scholarships WHERE id=?", (sid,)).fetchone()
    new_status = "NO_LONGER_VERIFIABLE" if permanent else "REVIEW_REQUIRED"
    if row["status"] != new_status:
        log_change(conn, sid, "status", row["status"], new_status, url, reason)
        stats["expired"] += 1
    conn.execute("UPDATE scholarships SET status=?, verification_label='REVIEW REQUIRED' WHERE id=?", (new_status, sid))

def upsert(conn, url, cls, rec, conf, parts, label, status, stats):
    ts = db.now()
    F = rec["fields"]
    new = {f: (F[f]["value"] if f in F else None) for f in FIELDS}
    row = conn.execute("SELECT * FROM scholarships WHERE official_source_url=?", (url,)).fetchone()
    common = dict(source_type=cls["source_type"], eligibility_json=json.dumps(rec["structured"]),
                  status=status, verification_label=label, confidence=conf,
                  confidence_breakdown=json.dumps(parts), last_verified=ts)
    if row is None:
        data = {**new, **common, "official_source_url": url, "first_discovered": ts, "last_changed": ts}
        conn.execute(f"INSERT INTO scholarships({','.join(data)}) VALUES ({','.join('?' * len(data))})", list(data.values()))
        sid = conn.execute("SELECT id FROM scholarships WHERE official_source_url=?", (url,)).fetchone()["id"]
        stats["discovered"] += 1
        print(f"  NEW  {new['name'][:70]}  [{status}, {conf}%]")
    else:
        old, sid, changed = dict(row), row["id"], False
        merged = {}
        for f in FIELDS:
            merged[f] = new[f] if new[f] is not None else old[f]       # never blank out known data
            if f in TRACKED and new[f] is not None and old[f] is not None and str(new[f]) != str(old[f]):
                log_change(conn, sid, f, old[f], new[f], url, F[f]["quote"])
                changed = True
        if old["status"] != status:
            log_change(conn, sid, "status", old["status"], status, url, F.get("closing_date", {}).get("quote", ""))
            changed = True
            if status == "EXPIRED":
                stats["expired"] += 1
        if changed:
            stats["updated"] += 1
        data = {**merged, **common, "last_changed": ts if changed else old["last_changed"]}
        conn.execute(f"UPDATE scholarships SET {','.join(k + '=?' for k in data)} WHERE id=?", list(data.values()) + [sid])
    for f, v in F.items():
        conn.execute("DELETE FROM evidence WHERE scholarship_id=? AND field=?", (sid, f))
        conn.execute("INSERT INTO evidence(scholarship_id,field,value,quote,source_url,captured_at) VALUES (?,?,?,?,?,?)",
                     (sid, f, v["value"], v["quote"], url, ts))

def process_url(conn, url, via, stats):
    """Returns links worth following when the page is a hub/listing rather than a single scholarship."""
    cls = classify_url(url)
    if cls["source_type"] == "AGGREGATOR":
        return []
    existing = conn.execute("SELECT id FROM scholarships WHERE official_source_url=?", (url,)).fetchone()
    page = fetch.fetch(url)
    if not page["ok"]:
        if existing:
            mark_unverifiable(conn, existing["id"], url, f"re-fetch failed: {page['error']}",
                              permanent=page["status"] in (404, 410), stats=stats)
        return []
    conn.execute("INSERT INTO pages(url,fetched_at,http_status,content_hash,text) VALUES (?,?,?,?,?)",
                 (url, db.now(), page["status"], page["content_hash"], page["text"]))
    cls = refine_source(cls, page)
    if not cls["is_official"]:
        return []
    single = extract.is_scholarship_page(page["text"]) and not extract.is_listing_page(page["text"])
    rec = extract.extract(page) if single else None
    if rec is not None:
        rec = verify.validate_fields(rec, page["text"])
    if rec is None or "name" not in rec["fields"]:
        if existing:
            mark_unverifiable(conn, existing["id"], url, "page no longer describes this scholarship", True, stats)
        return discover.expansion_links(page, cls)
    apply_url = rec["fields"].get("application_url", {}).get("value")
    apply_ok = fetch.url_alive(apply_url) if apply_url else None
    conf, parts, label = verify.score(rec, cls, page, apply_ok)
    upsert(conn, url, cls, rec, conf, parts, label, compute_status(rec), stats)
    return []

def run_crawl():
    db.init_db()
    conn = db.get_conn()
    stats = {"discovered": 0, "updated": 0, "expired": 0}
    started = db.now()
    print("== Discovery ==")
    cands = discover.discover(conn)
    for r in conn.execute("SELECT official_source_url FROM scholarships"):
        cands.setdefault(r["official_source_url"], "recheck")      
    queue = [(u, v, 0) for u, v in cands.items()]
    seen = set(cands)
    print(f"== Crawling (up to {config.MAX_PAGES} pages, depth {config.MAX_DEPTH}) ==")
    i = 0
    while i < len(queue) and i < config.MAX_PAGES:
        url, via, depth = queue[i]
        i += 1
        print(f"[{i}/{len(queue)}] d{depth} ({via}) {url}")
        try:
            more = process_url(conn, url, via, stats)
            conn.commit()
            if depth < config.MAX_DEPTH:
                for link in more:
                    if link not in seen:
                        seen.add(link)
                        queue.append((link, "depth-expansion", depth + 1))
        except Exception as e:
            print(f"  error: {e}")
    conn.execute("INSERT INTO crawl_runs(started_at,finished_at,discovered,updated,expired) VALUES (?,?,?,?,?)",
                 (started, db.now(), stats["discovered"], stats["updated"], stats["expired"]))
    conn.commit()
    print("== Done ==", stats)