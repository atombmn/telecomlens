# Changelog

All notable changes to TelecomLens are documented here.

---

## v4.0.0 — 2026-05-21

### Added
- **Divisions tab** — dedicated tab combining Division Manager, Bulk Retag, and Change Log into one focused workspace
- **Division Manager** — create, rename (cascades to all imported bills instantly), recolour with a colour picker, and delete divisions from the registry
- **Bulk Retag** — search lines by subscriber name, number, or tariff; filter by current division and/or bill scope; preview affected rows before committing; apply in one click
- **Change Log** — every division reassignment is recorded with entity, previous value, new value, timestamp, actor, and free-text reason/note
- **Rollback** — undo individual changes (↩ Undo button per row) or select multiple with checkboxes and bulk-rollback in one request; rolled-back entries are marked and excluded from future rollbacks
- **Division persistence** — `SubscriberProfile.division_override` carries manual assignments forward to future bill imports, so re-importing a bill does not lose your work
- **⏹ Stop button** — graceful server shutdown from the header bar; replaces needing `Ctrl+C` in the terminal; shows a "server stopped" confirmation screen after clicking
- **Import progress overlay** — full-screen progress bar with step-by-step status (file name, subscriber count, KES total) during large bill imports; dismisses automatically on completion
- **`BillUpload.outstanding_total`** — bill-level outstanding is now stored and displayed correctly (was always 0 before)
- **`BillUpload.total_net / total_vat / total_excise`** — all three tax components stored at bill level from the TAX ANALYSIS section (exact figures, not rounded line sums)
- **`POST /api/bills/{id}/reclassify`** — re-run smart classification on all lines in a bill without re-importing the PDF; respects existing `division_override` values
- **`GET /api/health/status`** — lightweight ping endpoint used by the UI to detect when the server has stopped
- **`GET /api/orgs/{id}/retag-preview`** — preview which lines a retag would affect (search + division filter) without committing

### Changed
- **UI consolidated from 9 tabs to 6** — Executive + Operations → Overview; ICT + Subscribers → Subscribers; Budget & Forecast + Trends → Analytics; Reports & Export + Integrations → Settings. Divisions is a new dedicated tab. Eliminates tab-bar overflow on normal screens.
- **Header bar simplified** — Customise button replaced by ⚙ gear icon that opens a settings drawer; Reclassify button only shown when a bill is loaded; Stop button replaces the old terminal-only `Ctrl+C` workflow
- **Parser completely rewritten** against real Safaricom postpay bill format:
  - Pages split by form-feed `\f`, not regex on `TAX INVOICE`
  - Subscriber name extracted from left side of the Invoice Number line (right-column layout)
  - Financial fields use the correct label patterns: `Amount Excluding VAT and Excise Duty`, `EXCISE - 15%`, `VAT - 16%`, `Amount Due   Ksh   <value>`
  - Account totals from TAX ANALYSIS section, not per-invoice lines
  - Outstanding from header `Amount Outstanding   Ksh   <value>`
  - Org name skips `POSTPAY BILL` and address lines
- **`bill_summary` endpoint** now uses stored bill-level totals (exact) and falls back to line-item sums only for older imports
- **Empty state guards** — Subscribers, Budget, and Integrations tabs now show a friendly "Import a bill first" message instead of an infinite spinner when no org/bill is selected

### Fixed
- Total Spend on Overview showing 0 — was using wrong regex pattern for `Total Amount Due`; fixed to search full text for `Gross Amount`
- Outstanding showing 0 — was looking for per-invoice field that doesn't exist; fixed to extract bill-level `Amount Outstanding`
- Pre-Tax, VAT, Excise all showing 0 — label patterns did not match real bill format; all three now correctly extracted
- Spend by Division chart not rendering — Chart.js SRI integrity hash was computed against `chart.umd.js` but URL pointed to `chart.umd.min.js`; hash corrected
- Subscribers tab infinite spinner — `loadSubscriberData` returned immediately on missing org without clearing the spinner
- Budget & Forecast infinite spinner — same root cause as Subscribers; fixed with empty state message
- Top Spenders showing all-zero amounts — `total_all_months` was being summed over records that had 0 amount_due_kes; fixed by using correct field
- Division donut chart not responding to clicks — onclick handler in Chart.js options referenced stale `S.divisions` index; now passes value directly
- Reclassify endpoint returning wrong field name — endpoint returned `changed` but frontend expected `changed_lines`

---

## v3.1.0 — 2026-05-10

### Added
- Multi-signal classifier — 7-level cascade: user rules → name keywords (20 patterns) → tariff keywords (8 patterns) → invoice block text → CDR service mix → tariff normalisation → spend-tier fallback; eliminates "all Unclassified" charts
- `classify_line()` function with `raw_name`, `tariff_plan`, `cdrs`, `block_text`, `amount_due` inputs
- CDR service-mix analysis: `_analyse_cdr_mix()` detects Data-Heavy, Voice-Heavy, SMS-Heavy lines from CDR records
- Tariff normalisation: `_normalise_tariff()` extracts clean category names from plan names

### Changed
- `store_bill` in main.py updated to call `classify_line()` with all available signals instead of name-only `classify_name()`
- `detect_anomalies()` updated to flag `Other / Unclassified` as an anomaly (in addition to old `Unclassified`)

---

## v3.0.0 — 2026-05-07

### Added
- Full FastAPI backend with SQLAlchemy SQLite (swappable to Postgres/MySQL)
- 44+ REST endpoints covering bills, subscribers, trends, budgets, alerts, webhooks, audit log, annotations, divisions
- `ChangeLog` model with `prev_value`, `new_value`, `rolled_back`, `rolled_back_at` fields
- `Division` model for org-specific division registry with colour and description
- `BudgetEntry` model for per-division monthly budget targets with headcount
- `SpendAlert` model with scope (total / division / subscriber) and threshold
- Webhook system with HMAC-SHA256 signing (`X-TelecomLens-Signature`)
- Bulk retag with dry-run preview
- Individual and bulk rollback endpoints
- `ensure_division()` helper — auto-registers new division names on retag
- `_log_change()` helper — logs every field change to ChangeLog
- Budget vs actual with variance and status badges (OK / ⚠ Near / ▲ Over)
- 3-month linear regression forecast with confidence bands
- Cost-per-head benchmarks by division
- Subscriber lifecycle detection (new activations, deactivations, plan changes across bills)
- Anomaly detection: high spend, zero charge with activity, high CDR count, unclassified
- Drill-down panel with sparkline history, top-3 contributors, full line items, CSV export
- Import folder endpoint (`/api/bills/import-folder`) for batch processing
- Chargeback Excel export (multi-sheet, one per division) via openpyxl
- Custom .docx report builder with section and division filters
- Annotation system for bill-level, line-level, and division notes
- Carrier detection (Safaricom, Airtel Kenya, Telkom Kenya, Faiba / JTL)
- Label customisation system — all tab names and section headings editable in-browser

### Security
- `sqlalchemy>=2.0.36` to fix Python 3.13/3.14 `__firstlineno__` crash
- `shutil.which()` replaces `subprocess.run(["which", ...])` (Windows-safe)
- `ilike()` wildcard escaping for `%` and `_` in search inputs
- `CORS_ORIGINS` env var (not hardcoded `*`)
- Lazy imports for `report` and `openpyxl` to prevent startup crash when optional packages are absent

---

## v2.0.0 — 2026-04-28

### Added
- Initial PDF parser for Safaricom postpay bills
- FastAPI + SQLite backend
- React-style single-file SPA dashboard
- Subscriber registry and tagging
- Basic CSV chargeback export
