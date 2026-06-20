"""Subscriber history endpoint integration test. Run: python tests/test_history.py"""
import os, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.mkdtemp(), 't.db')}"
sys.path.insert(0, REPO)
import main
from main import (SessionLocal, BillUpload, InvoiceLine, ChangeLog, subscriber_history)

NUM = "254700111222"
db = SessionLocal()
specs = [("feb.pdf", "10/02/2026"), ("apr.pdf", "12/04/2026"),
         ("jan.pdf", "11/01/2026"), ("mar.pdf", "09/03/2026")]
bills = {}
for fn, d in specs:
    b = BillUpload(org_id="acme", filename=fn, sha256=fn, statement_date=d,
                   statement_iso=main.statement_to_iso(d), account_total=0)
    db.add(b); db.flush(); bills[fn] = b


def line(bill, name, amt, tariff="Postpay 1000"):
    db.add(InvoiceLine(bill_id=bill.id, org_id="acme", invoice_number=f"{bill.filename}-{NUM}",
                       subscriber_number=NUM, raw_name=name, tariff_plan=tariff,
                       division="Sales", amount_due_kes=amt, cdr_count=10))


line(bills["jan.pdf"], "JOHN DOE", 1000)
line(bills["feb.pdf"], "J. DOE (SALES)", 1800)           # name change + 80% spike
line(bills["apr.pdf"], "J. DOE (SALES)", 1850, tariff="Postpay 2000")  # plan change, after gap
db.commit()
db.add(ChangeLog(org_id="acme", entity_type="invoice_line", entity_id="0700111222",
                 field="division", prev_value="Unclassified", new_value="Sales",
                 actor="admin", note="cleanup"))
db.commit(); db.close()

db = SessionLocal()
h = subscriber_history("acme", "0700 111 222", db=db)
db.close()

assert h["subscriber_number"] == NUM and h["display_number"] == "0700111222"
assert h["summary"]["bills_present"] == 3 and h["summary"]["bills_total"] == 4
assert h["summary"]["status"] == "active"
assert h["summary"]["first_seen"] == "11/01/2026" and h["summary"]["last_seen"] == "12/04/2026"
assert h["summary"]["lifetime_spend"] == 4650.0
assert [t["statement_iso"] for t in h["timeline"]] == ["2026-01-11", "2026-02-10", "2026-04-12"]
ev = {e["type"] for e in h["events"]}
assert {"first_seen", "name_change", "cost_spike", "plan_change", "reactivated"} <= ev and "gone" not in ev
assert any(c["field"] == "division" and c["new_value"] == "Sales" for c in h["changes"])
print("[PASS] timeline chronological, totals/status correct, events + cross-format audit OK")

db = SessionLocal()
empty = subscriber_history("acme", "0799999999", db=db); db.close()
assert empty["found"] is False and empty["timeline"] == [] and empty["summary"]["bills_total"] == 4
print("[PASS] unknown number returns clean empty shape")
print("\nALL HISTORY CHECKS PASSED")
