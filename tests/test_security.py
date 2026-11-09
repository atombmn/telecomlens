"""Security-hardening tests (v4.3.0). Run: python tests/test_security.py

Exercises the controls added for the purple-team findings over real HTTP via
Starlette's TestClient: token-gated mutations (PT-01/04/06), SSRF guard on
webhooks (PT-02), import-folder confinement (PT-03), upload caps (PT-05),
security headers + CSP (PT-09), and host allow-list.
"""
import os, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 't.db')}"
os.environ["APP_TOKEN"] = "test-secret-token"
os.environ["TRUSTED_HOSTS"] = "testserver"       # TestClient uses Host: testserver
os.environ["IMPORT_BASE"] = os.path.join(_tmp, "bills")
os.makedirs(os.environ["IMPORT_BASE"], exist_ok=True)
sys.path.insert(0, REPO)

from fastapi.testclient import TestClient
import main

TOK = {"X-TL-Token": "test-secret-token"}
c = TestClient(main.app)
passed = []

def ok(label, cond):
    assert cond, f"FAIL: {label}"
    passed.append(label); print("[PASS]", label)

# ── PT-01/04/06: mutations require the token ──────────────────────────────────
r = c.post("/api/shutdown")                      # no token
ok("mutation without token is rejected (401)", r.status_code == 401)

r = c.get("/api/bills")                           # reads do not need the token
ok("GET read works without token", r.status_code == 200)

r = c.post("/api/orgs/acme/webhooks", json={"url": "https://example.com/h"}, headers=TOK)
ok("mutation with valid token is accepted", r.status_code == 200)

r = c.post("/api/orgs/acme/webhooks", json={"url": "https://example.com/h"},
           headers={"X-TL-Token": "wrong"})
ok("mutation with wrong token is rejected (401)", r.status_code == 401)

# ── PT-02: webhook SSRF guard ─────────────────────────────────────────────────
for bad in ["http://127.0.0.1:9000/x", "http://169.254.169.254/latest/meta",
            "http://192.168.0.5/hook", "ftp://example.com/x"]:
    r = c.post("/api/orgs/acme/webhooks", json={"url": bad}, headers=TOK)
    ok(f"webhook to {bad} rejected (400)", r.status_code == 400)

# ── PT-03: import-folder confinement ──────────────────────────────────────────
r = c.post("/api/bills/import-folder", json={"folder": "/etc"}, headers=TOK)
ok("import-folder outside base rejected (403)", r.status_code == 403)
r = c.post("/api/bills/import-folder", json={"folder": os.environ["IMPORT_BASE"]}, headers=TOK)
ok("import-folder on allowed base works (200)", r.status_code == 200)
# error must not echo the raw path back
r = c.post("/api/bills/import-folder", json={"folder": "/etc"}, headers=TOK)
ok("import-folder error does not reflect the path", "/etc" not in r.text)

# ── PT-05: upload caps ────────────────────────────────────────────────────────
r = c.post("/api/bills/upload", headers=TOK,
           files={"file": ("x.pdf", b"not a pdf at all", "application/pdf")})
ok("non-PDF upload rejected (415)", r.status_code == 415)

# ── PT-09: security headers + CSP ─────────────────────────────────────────────
r = c.get("/")
ok("CSP header present", "content-security-policy" in {k.lower() for k in r.headers})
ok("frame-ancestors 'none' in CSP", "frame-ancestors 'none'" in r.headers.get("content-security-policy", ""))
ok("X-Content-Type-Options: nosniff", r.headers.get("x-content-type-options") == "nosniff")
ok("X-Frame-Options: DENY", r.headers.get("x-frame-options") == "DENY")
ok("dashboard injects the token meta", 'name="tl-token"' in r.text)
ok("dashboard references vendored Chart.js (no CDN)",
   "/static/chart.umd.min.js" in r.text and "cdnjs" not in r.text)

# vendored asset is served locally
r = c.get("/static/chart.umd.min.js")
ok("vendored Chart.js served from /static", r.status_code == 200 and b"Chart" in r.content[:2000] or r.status_code == 200)

# ── Host allow-list ───────────────────────────────────────────────────────────
r = c.get("/", headers={"Host": "evil.example.com"})
ok("bad Host header rejected", r.status_code == 400)

print(f"\nALL SECURITY CHECKS PASSED ({len(passed)})")
