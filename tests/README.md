# Tests

Run from the repo root with the project's virtualenv active (so dependencies
like `python-docx` are available). Each script sets up its own throwaway SQLite
database in a temp directory and exits non-zero on failure.

```bash
python tests/test_msisdn.py     # MSISDN normalisation unit tests (no DB)
python tests/test_backfill.py   # schema migration + one-time MSISDN/date backfill
python tests/test_history.py    # /subscribers/{n}/history endpoint
python tests/test_insights.py   # as_of guard, /waste, rollback, .docx report section
```

`test_msisdn.py` is pure-stdlib. The other three import `main`, which on import
runs the idempotent migration/backfill against the temp database — that is part
of what they verify.
