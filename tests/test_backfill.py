"""Migration + backfill integration test against a simulated old (v4.1) DB.
Run: python tests/test_backfill.py"""
import os, sys, sqlite3, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(tempfile.mkdtemp(), "telecomlens.db")
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"

# Pre-create bill_uploads WITHOUT statement_iso — the pre-upgrade schema.
con = sqlite3.connect(DB_PATH)
con.executescript("""
CREATE TABLE bill_uploads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    org_id VARCHAR, filename VARCHAR, sha256 VARCHAR UNIQUE,
    statement_date VARCHAR, account_total FLOAT, outstanding_total FLOAT,
    total_net FLOAT, total_vat FLOAT, total_excise FLOAT,
    subscriber_count INTEGER, uploaded_at DATETIME
);""")
con.commit(); con.close()

sys.path.insert(0, REPO)
import main  # runs create_all + _migrate_schema + _backfill_once

con = sqlite3.connect(DB_PATH)
cols = [r[1] for r in con.execute("PRAGMA table_info(bill_uploads)").fetchall()]
con.close()
assert "statement_iso" in cols, "migration did not add statement_iso"
print("[PASS] migration added bill_uploads.statement_iso to existing table")

from main import (SessionLocal, BillUpload, InvoiceLine, CDRRecord,
                  SubscriberProfile, AuditLog, _backfill_once, _BACKFILL_MARKER)

db = SessionLocal()
db.query(AuditLog).filter_by(action=_BACKFILL_MARKER).delete()
jan = BillUpload(org_id="acme", filename="jan.pdf", sha256="j1",
                 statement_date="15/01/2026", statement_iso="", account_total=100)
feb = BillUpload(org_id="acme", filename="feb.pdf", sha256="f1",
                 statement_date="03/02/2026", statement_iso="", account_total=120)
db.add_all([jan, feb]); db.flush()
db.add_all([
    InvoiceLine(bill_id=jan.id, org_id="acme", invoice_number="INV-J",
                subscriber_number="0722123456", raw_name="J. DOE", division="Sales", amount_due_kes=100),
    InvoiceLine(bill_id=feb.id, org_id="acme", invoice_number="INV-F",
                subscriber_number="254722123456", raw_name="J. DOE", division="Sales", amount_due_kes=120),
])
db.add(CDRRecord(bill_id=feb.id, subscriber_number="+254 722 123 456", date="01/02/2026",
                 time="09:00", destination="x", duration="60", rate=1.0, charge=2.0, service_type="voice"))
db.add_all([
    SubscriberProfile(org_id="acme", subscriber_number="0722123456", display_name="J. Doe",
                      first_seen_date="15/01/2026", last_seen_date="15/01/2026", tags="vip"),
    SubscriberProfile(org_id="acme", subscriber_number="254722123456", display_name="",
                      division_override="Sales", first_seen_date="03/02/2026",
                      last_seen_date="03/02/2026", tags="field"),
])
db.commit(); db.close()

_backfill_once()

db = SessionLocal()
bills = db.query(BillUpload).order_by(BillUpload.statement_iso).all()
assert [b.statement_iso for b in bills] == ["2026-01-15", "2026-02-03"]
assert [b.filename for b in bills] == ["jan.pdf", "feb.pdf"]
print("[PASS] statement_iso populated; chronological sort Jan->Feb correct")
assert {l.subscriber_number for l in db.query(InvoiceLine).all()} == {"254722123456"}
assert {c.subscriber_number for c in db.query(CDRRecord).all()} == {"254722123456"}
print("[PASS] invoice lines + CDR collapsed to canonical 254722123456")
profs = db.query(SubscriberProfile).filter_by(org_id="acme").all()
assert len(profs) == 1
p = profs[0]
assert p.subscriber_number == "254722123456"
assert p.first_seen_date == "15/01/2026" and p.last_seen_date == "03/02/2026"
assert p.display_name == "J. Doe" and p.division_override == "Sales"
assert set(p.tags.split(",")) == {"vip", "field"}
print("[PASS] duplicate profiles merged; first/last seen + fields correct")
before = (db.query(InvoiceLine).count(), db.query(SubscriberProfile).count())
db.close()
_backfill_once()
db = SessionLocal()
after = (db.query(InvoiceLine).count(), db.query(SubscriberProfile).count())
assert before == after
assert db.query(AuditLog).filter_by(action=_BACKFILL_MARKER).count() == 1
db.close()
print("[PASS] backfill is idempotent (no-op on second run)")
print("\nALL BACKFILL CHECKS PASSED")
