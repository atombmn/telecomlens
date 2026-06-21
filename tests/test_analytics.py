"""Quarterly/yearly analytics aggregation test. Run: python tests/test_analytics.py

Covers: month dedup (drop 0-sub draft duplicate), calendar quarter/year bucketing,
partial-bucket flagging (no annualisation), unparseable-date exclusion, and
native-vs-summed budgets with coverage reporting.
"""
import os, sys, tempfile
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.mkdtemp(), 't.db')}"
sys.path.insert(0, REPO)
import main
from main import (SessionLocal, BillUpload, InvoiceLine, BudgetEntry,
                  spend_trend, budget_vs_actual, _dedup_bills, _period_bucket)

db = SessionLocal()

def bill(iso, sd, total, subs, up):
    b = BillUpload(org_id="z", filename=iso, sha256=f"{iso}-{up}", statement_date=sd,
                   statement_iso=iso, account_total=total, subscriber_count=subs,
                   uploaded_at=datetime(2026, 6, 1, up))
    db.add(b); db.flush(); return b

def line(b, div, amt):
    db.add(InvoiceLine(bill_id=b.id, org_id="z", invoice_number=f"{b.id}-{div}",
                       subscriber_number="254722000001", raw_name="N", division=div,
                       amount_due_kes=amt, cdr_count=1))

# Q1 2026 full: Jan, Feb, Mar
for iso, sd, total, subs in [("2026-01-01", "01/01/2026", 300, 100),
                             ("2026-02-01", "01/02/2026", 350, 110),
                             ("2026-03-01", "01/03/2026", 400, 120)]:
    line(bill(iso, sd, total, subs, 1), "Sales", total)
# Duplicate Jan draft: 0 subs, later upload -> must be dropped by dedup
line(bill("2026-01-01", "01/01/2026", 999, 0, 9), "Sales", 999)
# Q2 2026 partial: only April
line(bill("2026-04-01", "01/04/2026", 500, 130, 4), "Sales", 500)
# Unparseable-date bill -> excluded from all buckets
be = BillUpload(org_id="z", filename="bad", sha256="bad", statement_date="",
                statement_iso="", account_total=123, subscriber_count=5)
db.add(be); db.flush(); line(be, "Sales", 123)
# Budgets: monthly Jan + Feb (no Mar), and a native quarterly budget for Q2
db.add(BudgetEntry(org_id="z", division="Sales", period="2026-01", budget_kes=320, headcount=10))
db.add(BudgetEntry(org_id="z", division="Sales", period="2026-02", budget_kes=360, headcount=11))
db.add(BudgetEntry(org_id="z", division="Sales", period="2026-Q2", budget_kes=2000, headcount=40))
db.commit(); db.close()

# --- helpers ---
assert _period_bucket("2026-03-01", "quarter")[0] == "2026-Q1"
assert _period_bucket("2026-04-01", "quarter")[0] == "2026-Q2"
assert _period_bucket("2026-07-01", "year")[0] == "2026"
print("[PASS] period bucketing (calendar Q/Y)")

db = SessionLocal()
dd = _dedup_bills(db.query(BillUpload).filter_by(org_id="z").all())
jan = [b for b in dd if b.statement_iso == "2026-01-01"]
assert len(jan) == 1 and jan[0].subscriber_count == 100, "dedup should keep the 100-sub Jan bill"
assert all(b.statement_iso for b in dd), "blank-date bill must be excluded"
assert len(dd) == 4, f"expected 4 months after dedup, got {len(dd)}"
print("[PASS] month dedup keeps real bill, drops 0-sub draft, excludes blank date")

# --- spend trend ---
tr_m = spend_trend("z", granularity="month", db=db)
assert [r["account_total"] for r in tr_m] == [300, 350, 400, 500], "Jan must be 300 not 999"
tr_q = {r["period"]: r for r in spend_trend("z", granularity="quarter", db=db)}
assert tr_q["2026-Q1"]["account_total"] == 1050 and not tr_q["2026-Q1"]["partial"]
assert tr_q["2026-Q1"]["months_included"] == 3
assert tr_q["2026-Q2"]["account_total"] == 500 and tr_q["2026-Q2"]["partial"]
assert tr_q["2026-Q2"]["months_included"] == 1 and tr_q["2026-Q2"]["months_expected"] == 3
tr_y = spend_trend("z", granularity="year", db=db)
assert tr_y[0]["account_total"] == 1550 and tr_y[0]["partial"] and tr_y[0]["months_included"] == 4
print("[PASS] spend trend: dedup'd month, full Q1, partial Q2/year, no annualisation")

# --- budget vs actual ---
bva_q = {r["period"]: r for r in budget_vs_actual("z", granularity="quarter", db=db)}
q1 = bva_q["2026-Q1"]
assert q1["total_actual"] == 1050 and q1["total_budget"] == 680, "Q1 budget = 320+360 summed"
assert q1["budget_source"] == "summed" and q1["months_budgeted"] == 2 and q1["months_included"] == 3
q2 = bva_q["2026-Q2"]
assert q2["total_budget"] == 2000 and q2["budget_source"] == "native", "Q2 uses native quarterly target"
# monthly default still works and is dedup'd
bva_m = budget_vs_actual("z", granularity="month", db=db)
jan_m = [r for r in bva_m if r["period"] == "2026-01"][0]
assert jan_m["total_actual"] == 300, "monthly BVA must also be dedup'd"
print("[PASS] budget vs actual: summed (2/3 coverage) vs native quarterly; monthly dedup'd")
db.close()
print("\nALL ANALYTICS CHECKS PASSED")
