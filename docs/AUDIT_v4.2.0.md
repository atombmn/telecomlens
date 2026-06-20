# TelecomLens — System Audit (v4.2.0)

**Date:** 2026-06-20
**Scope:** Full once-over of the codebase prior to packaging the v4.2.0 release.
**Result:** Release-ready. All findings below were resolved or are documented as accepted risks for the local-tool threat model.

---

## 1. Files reviewed

| File | Status |
|------|--------|
| `main.py` | Reviewed — models, import path, migration/backfill, all endpoints incl. new history/waste, report wiring |
| `parser.py` | Reviewed — pure extractor, stdlib-only imports |
| `discover.py` | Reviewed — ReDoS-guarded classification |
| `msisdn.py` | Reviewed — new normalisation module |
| `report.py` | Reviewed — docx generator + new section |
| `static/index.html` | Reviewed — SPA; JS syntax-checked with `node --check` |
| `requirements.txt`, `.env.example`, `.gitignore` | Reviewed |
| `install/start/stop` (`.bat`/`.sh`) | Reviewed — line endings checked |
| `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md` | Updated for v4.2.0 |

---

## 2. Findings & resolutions

| # | Severity | Finding | Resolution |
|---|----------|---------|------------|
| 1 | Medium | `FastAPI(version=…)` was `3.1.0` — stale, did not match the v4.x release line | Bumped to `4.2.0` |
| 2 | Medium (Windows) | `start.bat` and `stop.bat` were saved with LF endings; `cmd.exe` can mis-parse LF batch files | Converted to CRLF (verified CR == LF byte counts) |
| 3 | Medium | No `.gitattributes`, so line endings could regress on checkout/commit across OSes | Added `.gitattributes` (CRLF for `*.bat`, LF for `*.sh` and source) |
| 4 | High (regression) | The `GET /api/orgs/{org_id}/tags` route decorator was inadvertently dropped while adding the history endpoint, which would have 404'd the Tags subtab | Restored; route registration asserted in a startup check |
| 5 | Low | `subscriber_cdr` filtered on the raw `sub_number` rather than the canonical form | Now normalises the path parameter |
| 6 | Low | Docs (`README`, `CHANGELOG`) did not cover history, waste, normalisation, or the migration behaviour | Updated both; added this audit |

---

## 3. New code review (v4.2.0 additions)

- **MSISDN normalisation** — idempotent and conservative (non-mobile identifiers pass through unchanged). 17 format cases under test. Applied at the single persistence choke point in `store_bill`, plus the exact-match search sites, the profile PATCH, and the CDR endpoint.
- **Migration + backfill** — SQLite-only `ALTER TABLE` guarded by a `PRAGMA` existence check; backfill guarded by an `AuditLog` marker so it runs once. Each operation is individually idempotent, so an interrupted run is safely retried on next startup. Duplicate-profile merge handles collisions created by normalisation (earliest first-seen / latest last-seen, non-empty field preference, unioned tags).
- **Chronology** — all ten `ORDER BY` sites moved from the lexicographic `statement_date` string to the new indexed `statement_iso` (`YYYY-MM-DD`). This also corrected a latent defect in the pre-existing lifecycle/trend/forecast features.
- **History endpoint** — derived events use only presence-stable fields (name, tariff, presence, amount); division/tag history is sourced from the `ChangeLog` audit trail (matched across pre-normalisation number formats), never from diffing the mutable `InvoiceLine.division`. Queries are bounded (one number's lines; changes capped at 200).
- **`as_of` guard** — windows the analysis to bills on/before a given period so a partial or future-dated bill cannot flip status/lifecycle.
- **Waste / report** — share one `_compute_waste` implementation so the Waste subtab and the `.docx` section cannot diverge.

---

## 4. Carried-forward protections (re-verified)

- **ReDoS** — `discover.py` caps pattern length (200) and blocks catastrophic constructs before compiling user rules.
- **Unbounded queries** — the CDR endpoint caps at 5,000 rows; new endpoints are inherently bounded.
- **Duplicate bills** — upload and folder-import both de-duplicate on SHA-256 of the file bytes.
- **Division-by-zero** — delta/percentage calculations guard zero denominators (history timeline, waste increases, lifecycle).
- **Dependency pinning** — minimum-version (`>=`) pins for Python 3.11–3.14 compatibility; all runtime imports (`fastapi`, `uvicorn`, `python-multipart`, `sqlalchemy`, `pydantic-settings`, `python-docx`, `openpyxl`, `httpx`, `psutil`) are present in `requirements.txt`.
- **pip robustness** — `install.bat` uses `python -m pip` with retry/timeout flags.

---

## 5. Accepted risks (local-tool threat model)

TelecomLens is designed to run on `localhost` on a single operator machine.

- **`POST /api/bills/import-folder`** reads PDFs from an operator-supplied server path. This is arbitrary filesystem read by design, acceptable because the operator already has filesystem access on their own machine. **Do not expose this instance to untrusted networks.** For shared/networked deployments, restrict `CORS_ORIGINS` and place the app behind authentication.
- **`POST /api/shutdown`** is unauthenticated (it powers the in-UI Stop button) — same local-only assumption applies.

---

## 6. Verification performed

```
py_compile: main.py parser.py discover.py msisdn.py report.py  — OK
node --check (extracted SPA <script>)                          — OK
tests/test_msisdn.py     — ALL PASS (17 cases + idempotency + display)
tests/test_backfill.py   — migration + backfill + merge + idempotency
tests/test_history.py    — timeline/order/events/cross-format audit + empty shape
tests/test_insights.py   — as_of guard + waste + rollback + .docx section
route registration       — /tags, /waste, /subscribers/{n}/history all present
report content           — "Subscriber Lifecycle & Waste" section present in .docx
```
