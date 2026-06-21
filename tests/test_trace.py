"""number-search (Trace tab) endpoint test. Run: python tests/test_trace.py"""
import os, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(tempfile.mkdtemp(), 't.db')}"
sys.path.insert(0, REPO)
import main
from main import SessionLocal, BillUpload, InvoiceLine, Organisation, number_search

NUM = "254722123456"
db = SessionLocal()
db.add(Organisation(id="acme", name="Acme Ltd", account_number="A1"))
for iso, sd, amt in [("2024-12-01", "01/01/2025", 100),
                     ("2025-01-01", "01/02/2025", 120),
                     ("2025-02-01", "01/03/2025", 140)]:
    b = BillUpload(org_id="acme", filename=f"bill_{iso}.pdf", sha256=iso,
                   statement_date=sd, statement_iso=iso, account_total=0)
    db.add(b); db.flush()
    db.add(InvoiceLine(bill_id=b.id, org_id="acme", invoice_number=f"i_{iso}",
                       subscriber_number=NUM, raw_name="J DOE", division="Sales",
                       tariff_plan="P1", amount_due_kes=amt, cdr_count=5))
# an unrelated number in just one bill
db.add(InvoiceLine(bill_id=b.id, org_id="acme", invoice_number="other",
                   subscriber_number="254733999000", raw_name="X", division="Ops",
                   amount_due_kes=9, cdr_count=1))
db.commit(); db.close()

db = SessionLocal()
desc = number_search(q="0722123456", order="desc", db=db)
asc = number_search(q="722123", order="asc", db=db)          # partial
other = number_search(q="0733", order="desc", db=db)
none = number_search(q="9999999", db=db)
db.close()

assert desc["instance_count"] == 3, desc["instance_count"]
assert [i["statement_date"] for i in desc["instances"]] == ["01/03/2025", "01/02/2025", "01/01/2025"]
assert desc["distinct_numbers"][0]["display_number"] == "0722123456"
assert desc["distinct_numbers"][0]["count"] == 3
print("[PASS] full number -> 3 instances, newest-first ordering, distinct summary")

assert [i["statement_date"] for i in asc["instances"]] == ["01/01/2025", "01/02/2025", "01/03/2025"]
print("[PASS] partial match + oldest-first ordering")

assert other["instance_count"] == 1 and other["instances"][0]["subscriber_number"] == "254733999000"
assert none["instance_count"] == 0
print("[PASS] specificity (0733 -> other line; non-match -> empty)")
print("\nALL TRACE CHECKS PASSED")
