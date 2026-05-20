# Changelog

All notable changes to TelecomLens are documented here.

---

## [3.2.0] — 2026-05

### Added — Reporting & Export
- **Custom Report Builder**: choose which sections to include (summary, tax recon, divisions, subscribers, anomalies, trends, annotations) and filter by division before generating the .docx
- **Per-division Excel chargeback packs**: multi-sheet `.xlsx` workbook — one worksheet per division plus a Summary sheet; anomalous lines highlighted in red; TOTAL formula row on each sheet
- **Inline Annotations**: attach notes to any bill, subscriber line, division, or anomaly; annotations appear as footnotes in exported reports
- New export endpoint: `POST /api/bills/{id}/report-custom.docx`
- New export endpoint: `GET /api/bills/{id}/chargeback-excel.xlsx`
- Annotation CRUD: `GET/POST /api/bills/{id}/annotations`, `DELETE /api/bills/{id}/annotations/{id}`

### Added — Data & Integrations
- **Audit Trail**: immutable log of every user action (bill imports, report exports, subscriber updates, webhook events); viewable in the Data & Integrations tab
- **Outbound Webhooks**: POST JSON payload to any URL after each bill import; optional HMAC-SHA256 signing via `X-TelecomLens-Signature`; test-ping endpoint
- **Carrier Detection**: auto-detects Safaricom, Airtel Kenya, Telkom Kenya, and Faiba/JTL from bill headers; viewable per-org in the Carriers sub-view
- New DB models: `Annotation`, `AuditLog`, `WebhookConfig`
- New endpoints: webhooks CRUD + test, audit log, carrier detection

### Added — Dashboard
- **Reports & Export tab** with three sub-views: Report Builder, Excel Packs, Annotations
- **Data & Integrations tab** with three sub-views: Audit Trail, Webhooks, Carrier Detection
- Both tabs fully integrated into the label-edit system (all headings customisable)

---

## [3.1.0] — 2026-05

### Added — Subscriber Management
- **Subscriber Registry**: searchable, filterable table of all known lines across all bills; per-line edit modal for display name, division override, tags, device type, expected tariff, notes
- **Tags**: apply comma-separated labels to subscribers; bulk-tag filtered views; tag manager board showing frequency and untagged lines
- **Lifecycle Tracker**: detects new activations, deactivations, and tariff plan changes across consecutive bills
- New DB model: `SubscriberProfile` with first/last-seen tracking
- New endpoints: `GET/PATCH /api/orgs/{id}/subscribers`, `GET /api/orgs/{id}/tags`, `GET /api/orgs/{id}/lifecycle`

### Added — Budget & Forecasting
- **Budget vs Actual**: per-division actual vs budget table with status badges; dotted budget overlay on trend chart; CSV import + download template
- **3-month Spend Forecast**: linear regression with confidence bands (±1 std-dev of residuals); history + forecast table
- **Spend Alerts**: KES ceilings per subscriber, division, or total bill; red breach banner in dashboard; breach detection endpoint
- **Cost-per-Head Benchmarks**: cost-per-employee ranking once headcount is set in budget editor
- New DB models: `BudgetEntry`, `SpendAlert`
- New endpoints: budgets CRUD + CSV import, `budget-vs-actual`, `forecast`, alerts CRUD + breach detection

---

## [3.0.0] — 2026-05

### Added — Editable Labels
- Every tab name, KPI card title, and section heading is editable via a ✎ Customise drawer
- Labels persist in `localStorage` under `tl_labels`; instant in-line pencil icons on section headings
- Reset-to-defaults button

### Added — Drill-Down Panel
- Clicking any KPI card, chart bar/segment, or table row opens a 420px side panel
- Panel contains: stats bar (KES total, line count, % of bill), sparkline history, top-3 contributors with bars, full line-items table with anomaly highlighting, filtered CSV export
- New backend endpoint: `GET /api/bills/{id}/drilldown?by=division|subscriber|tariff|anomaly|geography&value=X`

### Fixed — Report download
- `report.py` now lazily imported (app no longer crashes on startup if `python-docx` is absent)
- Report button uses `fetch()` + Blob download (not `target="_blank"`)
- Loading state and user-friendly error messages with install instructions

---

## [2.0.0] — 2026-04

### Added
- Multi-bill trend analysis across months
- Top-spender tracking across all imported bills
- Anomaly detection (zero charge with activity, high spend >50K, high CDR count, unclassified lines)
- Division mapping rules engine with regex patterns + priority ordering
- GL account mapping per division
- Chargeback CSV export

---

## [1.0.0] — 2026-03

### Initial release
- PDF bill ingestion via pdftotext
- Subscriber-level invoice parsing
- Executive, Finance, ICT, Operations, Trends tabs
- SQLite storage with SQLAlchemy ORM
- FastAPI backend, single-file HTML/JS dashboard
