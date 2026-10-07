import json, os, sys, sqlite3
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.append(ROOT)
import config

app = FastAPI(title="Scholarship Intelligence API")
app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")

def q(sql, params=()):
    conn = sqlite3.connect(os.path.join(ROOT, config.DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()

@app.get("/")
def home():
    return FileResponse(os.path.join(HERE, "static", "index.html"))

@app.get("/api/stats")
def stats():
    week = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(timespec="seconds")
    r = q("""SELECT COUNT(*) total,
                    SUM(verification_label='VERIFIED') verified,
                    SUM(verification_label!='VERIFIED') review,
                    SUM(status IN ('ACTIVE','EXPIRING_SOON')) active,
                    SUM(status='EXPIRED') expired,
                    SUM(status='NO_LONGER_VERIFIABLE') unverifiable,
                    SUM(last_changed>=?) recent,
                    ROUND(AVG(confidence),1) avg_conf
             FROM scholarships""", (week,))[0]
    r["changes"] = q("SELECT COUNT(*) n FROM change_log")[0]["n"]
    return {k: (v or 0) for k, v in r.items()}

@app.get("/api/scholarships")
def list_scholarships(search: str = "", status: str = "", label: str = "", source_type: str = ""):
    sql = ("SELECT id,name,provider,amount,closing_date,status,verification_label,confidence,"
           "source_type,last_verified FROM scholarships WHERE 1=1")
    p = []
    if search:
        sql += " AND (name LIKE ? OR provider LIKE ? OR income_criteria LIKE ? OR category_criteria LIKE ?)"
        p += [f"%{search}%"] * 4
    if status:
        sql += " AND status=?"; p.append(status)
    if label:
        sql += " AND verification_label=?"; p.append(label)
    if source_type:
        sql += " AND source_type=?"; p.append(source_type)
    return q(sql + " ORDER BY confidence DESC", p)

@app.get("/api/scholarships/{sid}")
def detail(sid: int):
    rows = q("SELECT * FROM scholarships WHERE id=?", (sid,))
    if not rows:
        raise HTTPException(status_code=404, detail="Scholarship not found")
    s = rows[0]
    s["eligibility"] = json.loads(s.pop("eligibility_json") or "{}")
    s["breakdown"] = json.loads(s.pop("confidence_breakdown") or "[]")
    s["evidence"] = q("SELECT field,value,quote,source_url,captured_at FROM evidence WHERE scholarship_id=?", (sid,))
    s["changes"] = q("SELECT field,old_value,new_value,detected_at,source_url,evidence_quote "
                     "FROM change_log WHERE scholarship_id=? ORDER BY detected_at DESC", (sid,))
    return s