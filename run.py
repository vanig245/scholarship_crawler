import sys, csv
from datetime import date, timedelta
import db
from crawler.pipeline import run_crawl

def simulate_change(n=2):
    """Rewinds stored deadlines to mimic a PREVIOUS crawl state; the next real crawl then detects the difference."""
    conn = db.get_conn()
    rows = conn.execute("SELECT id,name,closing_date FROM scholarships WHERE closing_date GLOB '[0-9][0-9][0-9][0-9]-*' "
                        "ORDER BY confidence DESC LIMIT ?", (n,)).fetchall()
    for r in rows:
        old = (date.fromisoformat(r["closing_date"]) - timedelta(days=14)).isoformat()
        conn.execute("UPDATE scholarships SET closing_date=? WHERE id=?", (old, r["id"]))
        print(f"rewound '{r['name'][:50]}' deadline {r['closing_date']} -> {old}")
    conn.commit()

def simulate_removal(n=2):
    """Points records at a non-existent page to exercise NO_LONGER_VERIFIABLE detection."""
    conn = db.get_conn()
    rows = conn.execute("SELECT id,name,official_source_url FROM scholarships ORDER BY confidence ASC LIMIT ?", (n,)).fetchall()
    for r in rows:
        conn.execute("UPDATE scholarships SET official_source_url=? WHERE id=?",
                     (r["official_source_url"].rstrip("/") + "/__simulated_removed__", r["id"]))
        print(f"simulated removal for '{r['name'][:50]}'")
    conn.commit()

def export():
    conn = db.get_conn()
    for table in ("scholarships", "change_log", "evidence"):
        rows = conn.execute(f"SELECT * FROM {table}").fetchall()
        if rows:
            with open(f"data/{table}.csv", "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(rows[0].keys())
                w.writerows([tuple(r) for r in rows])
            print(f"exported data/{table}.csv ({len(rows)} rows)")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "crawl"
    {"init": db.init_db, "crawl": run_crawl, "simulate-change": simulate_change,
     "simulate-removal": simulate_removal, "export": export}[cmd]()