"""as_of guard, waste insights, rollback, and .docx generation.
Run: python tests/test_insights.py"""
import os, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.mkdtemp(), 't.db')}"
sys.path.insert(0, REPO)
import main
from main import (SessionLocal, BillUpload, InvoiceLine, SubscriberProfile, ChangeLog,
                  subscriber_history, waste_insights, rollback_change, _compute_waste)

db = SessionLocal()
B = {}
for fn, d in [("jan", "10/01/2026"), ("feb", "10/02/2026"), ("mar", "10/03/2026")]:
    b = BillUpload(org_id="acme", filename=fn, sha256=fn, statement_date=d,
                   statement_iso=main.statement_to_iso(d), account_total=0)
    db.add(b); db.flush(); B[fn] = b


def L(bill, num, name, amt, cdr, div="Sales"):
    db.add(InvoiceLine(bill_id=bill.id, org_id="acme", invoice_number=f"{bill.filename}-{num}",
                       subscriber_number=num, raw_name=name, tariff_plan="P1", division=div,
                       amount_due_kes=amt, cdr_count=cdr))


L(B["jan"], "254700000001", "ALICE", 400, 20)
L(B["feb"], "254700000001", "ALICE", 450, 22)
L(B["mar"], "254700000001", "ALICE", 500, 0)          # billed, zero usage -> dormant
L(B["jan"], "254700000002", "BOB", 300, 10)
L(B["feb"], "254700000002", "BOB", 900, 30)            # absent in Mar -> deactivated
db.add(SubscriberProfile(org_id="acme", subscriber_number="254700000001", display_name="Alice",
                         first_seen_date="10/01/2026", last_seen_date="10/03/2026",
                         division_override="Sales"))
db.commit()
db.add(ChangeLog(org_id="acme", entity_type="invoice_line", entity_id="254700000001",
                 field="division", prev_value="Unclassified", new_value="Sales", actor="admin"))
db.commit(); db.close()

db = SessionLocal()
h_feb = subscriber_history("acme", "254700000002", as_of="2026-02", db=db)
h_latest = subscriber_history("acme", "254700000002", db=db)
db.close()
assert h_feb["summary"]["status"] == "active" and h_feb["summary"]["bills_total"] == 2
assert "gone" not in {e["type"] for e in h_feb["events"]}
assert h_latest["summary"]["status"] == "gone" and "gone" in {e["type"] for e in h_latest["events"]}
assert len(h_latest["available_periods"]) == 3
print("[PASS] as_of guard pins the reference period")

db = SessionLocal()
w = waste_insights("acme", db=db); db.close()
assert w["reference_period"] == "10/03/2026"
assert "254700000001" in {x["subscriber_number"] for x in w["dormant_billed"]}
assert "254700000002" in {x["subscriber_number"] for x in w["deactivated"]}
assert w["summary"]["dormant_billed_kes"] == 500.0
print("[PASS] waste: dormant-but-billed + deactivations detected")

db = SessionLocal()
cid = db.query(ChangeLog).filter_by(entity_id="254700000001").first().id
rollback_change("acme", cid, db=db); db.close()
db = SessionLocal()
divs = {l.division for l in db.query(InvoiceLine).filter_by(subscriber_number="254700000001").all()}
done = db.query(ChangeLog).filter_by(id=cid).first().rolled_back
db.close()
assert divs == {"Unclassified"} and done is True
print("[PASS] rollback reverted invoice-line division and flagged the change")

from report import generate_report
data = {"org_name": "Acme", "account_number": "123", "statement_date": "10/03/2026",
        "summary": {"account_total": 1000, "pre_tax_total": 800, "excise_total": 100,
                    "vat_total": 100, "outstanding_total": 0, "subscriber_count": 2, "anomaly_count": 1},
        "divisions": [{"division": "Sales", "total": 1000, "count": 2}],
        "anomalies": [], "top_subscribers": [], "trends": []}
db = SessionLocal(); data["waste"] = _compute_waste("acme", db); db.close()
docx = generate_report(data)
assert docx[:2] == b"PK" and len(docx) > 5000
print(f"[PASS] report generated with waste section ({len(docx):,} bytes)")
print("\nALL INSIGHTS CHECKS PASSED")
