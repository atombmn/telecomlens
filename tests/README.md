# Tests

Run from the repo root with the project's virtualenv active (so dependencies
like `python-docx` are available). Each script sets up its own throwaway SQLite
database in a temp directory and exits non-zero on failure.

```bash
python tests/test_msisdn.py     # MSISDN normalisation unit tests (no DB)
python tests/test_backfill.py   # schema migration + one-time MSISDN/date backfill
python tests/test_history.py    # /subscribers/{n}/history endpoint
python tests/test_insights.py   # as_of guard, /waste, rollback, .docx report section
python tests/test_trace.py      # cross-bill number search (/api/number-search)
python tests/test_analytics.py  # quarter/year roll-ups, dedup, native/summed budgets
python tests/test_security.py   # auth token, webhook SSRF, CSP/headers, upload caps, host allow-list
```

`test_msisdn.py` is pure-stdlib. The others import `main`, which on import runs
the idempotent migration/backfill against the temp database — that is part of
what they verify. `test_security.py` drives the app over HTTP with
`TestClient`; it sets `APP_TOKEN` and `TRUSTED_HOSTS=testserver` before import,
so it exercises the real middleware (token gate, host allow-list, CSP headers).
