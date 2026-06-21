# 📡 TelecomLens

**TelecomLens** is a self-hosted telecom bill analytics dashboard for organisations that receive monthly Safaricom postpay invoices. It turns raw PDF bills into actionable spend intelligence — with full division management, bulk re-tagging, a reversible change log, budget vs actual, forecasting, and clean one-click exports.

---

## What's new in v4.2

- **Per-number history** — click any subscriber (in the Registry, Lifecycle, Waste, Trace, or a bill drill-down) to open a cross-bill profile: spend-over-time chart, a derived activity feed (first seen, name/plan changes, cost spikes/drops, dormancy, reactivation, deactivation), the full manual-change audit with one-click **Undo**, and a per-period table. Pin any past period with the **As of** selector
- **Trace tab** — search any subscriber number across *every* uploaded bill at once (any format or partial digits). See one row per bill it appears in, sorted by date, and expand any instance to drill into that bill's call records — answering "when did this number first appear and how has it moved over time" in one place
- **Waste insights** — a new **Subscribers → Waste** subtab (and report section) surfacing lines billed without any usage, the biggest month-on-month increases, and lines that dropped off — the numbers most worth a second look
- **Canonical phone-number matching** — `0722…`, `254722…` and `+254 722…` are now treated as one line everywhere, so a number's history is never split by formatting differences. Existing databases are upgraded automatically on first launch
- **Correct chronology** — bills now sort by a proper date key; fixes subtle mis-ordering that affected lifecycle detection, trend sparklines, and the forecast when bills spanned multiple months
- **Reliable Windows line endings** — `.gitattributes` enforces CRLF on `.bat` and LF on `.sh`

## What's new in v4.1

- **Smart org detection** — all tabs (Subscribers, Divisions, Analytics, Settings) auto-detect the organisation from imported bills; no more "Import a bill first" screens when data already exists
- **Better search** — subscriber and retag searches use exact match for phone numbers (7+ digits) and partial match for name/tariff fragments; raw_name from invoice lines is now also searched
- **System resource monitor** — RAM/CPU indicator in the header; polls every 30 seconds; colour-coded (green/amber/orange); psutil-powered
- **Analytics bill comparisons** — explicit bill comparison dropdown above the Analytics subtabs when multiple bills are imported
- **Retag improvements** — bill scope dropdown lists all imported bills; "Move to division" is now a select + input hybrid to prevent typos
- **Terminal stays open** — the Stop button now stops the server and keeps the terminal window open with a "press any key to close" prompt

## What's new in v4.0

- **Division Manager** — create, rename (cascades across all bills), recolour, and manage your org's full division list
- **Bulk Retag** — search lines by name, number, or tariff; preview affected rows; move them to any division in one click
- **Change Log & Rollback** — every division reassignment is logged with who made it and why; undo individual changes or bulk-rollback a selection
- **Graceful Stop** — a Stop button in the header cleanly shuts the server down without needing the terminal
- **Cleaner UI** — 9 tabs consolidated to 6 (Overview, Finance, Subscribers, Divisions, Analytics, Settings); no more tab overflow on normal screens
- **Accurate parser** — re-calibrated against a real Safaricom postpay bill; all financial fields (pre-tax, excise, VAT, outstanding, total) now extract correctly
- **Import progress overlay** — a full-screen progress bar replaces the silent hang during large imports

---

## Features

| Tab | What you see |
|-----|-------------|
| **Overview** | KPI tiles (spend, outstanding, subscribers, anomalies), division donut + charge components charts, division detail table, anomaly register |
| **Finance** | Pre-tax / excise / VAT reconciliation with expected vs actual, chargeback register, one-click CSV / Excel / .docx export |
| **Subscribers** | Registry (search, filter by division/tag), per-number cross-bill history with activity feed and rollback, lifecycle events (activations, deactivations, plan changes), waste insights (billed-but-unused, top movers, drop-offs), tag manager |
| **Divisions** | Division Manager (create/rename/recolour), Bulk Retag tool, Change Log with individual and bulk rollback |
| **Analytics** | Spend trend, budget vs actual, 3-month forecast with confidence bands, spend alerts, cost-per-head benchmarks |
| **Settings** | Custom report builder (.docx), Excel chargeback pack, annotations, webhooks, audit trail, carrier detection |

**Drill-down on everything** — click any KPI tile, chart bar/segment, or table row to open a side panel with the exact line items, a sparkline history, top-3 contributors, and a filtered CSV export.

**Customise all labels** — every tab name, KPI title, and section heading is editable via the ⚙ button; changes persist in the browser.

---

## Requirements

| | Minimum |
|-|---------|
| Python | 3.10+ (3.13 / 3.14 fully supported) |
| pdftotext | Installed automatically on Windows by `install.bat` |
| Disk | ~50 MB for app; ~1 MB per bill imported |

---

## Quick start

### Windows
```bat
git clone https://github.com/atombmn/telecomlens.git
cd telecomlens
install.bat       :: one-time setup
start.bat         :: launch + open browser
```

### Linux / macOS
```bash
git clone https://github.com/atombmn/telecomlens.git
cd telecomlens
chmod +x install.sh start.sh
./install.sh      # one-time setup
./start.sh        # launch + open browser
```

Open **http://localhost:8000**, then click **⊕ Import** to load your first bill.

To stop the server: click **⏹ Stop** in the header, or press `Ctrl+C` in the terminal.

---

## Configuration (`.env`)

```ini
DATABASE_URL=sqlite:///./telecomlens.db   # swap for Postgres/MySQL in production
BILLS_FOLDER=bills                         # folder for batch folder imports
POPPLER_PATH=poppler                       # Windows only: path to Poppler bin
CORS_ORIGINS=*                             # restrict to IP for shared deployments
```

---

## Division management workflow

1. **Import a bill** — lines are auto-classified by tariff plan, subscriber name, CDR mix, and invoice block text
2. **Open Divisions → Bulk Retag** — search for lines by name/number/tariff; preview what will change; set the target division; apply
3. **Check the Change Log** — every change is listed with timestamp and note; tick boxes and click "Rollback selected" to undo
4. **Rename a division** — go to Divisions → Division Manager → Rename; the new name cascades to all imported bills instantly
5. **Re-import future bills** — subscriber profiles carry the division overrides forward, so future imports are already pre-classified

---

## Budget & Forecast

1. **Analytics → Budget vs Actual** → click **✎ Edit Budgets** to enter monthly KES targets per division, or download the CSV template, fill it in, and upload
2. The trend chart shows a dotted budget line; the table shows variance and a colour-coded status badge per division
3. **Analytics → Alerts** → add spend ceilings per subscriber, division, or total bill; a red breach banner appears when the latest bill exceeds any threshold
4. **Analytics → Forecast** → 3-month linear regression with confidence bands, based on all imported bill history

---

## Exporting

| Export | How |
|--------|-----|
| Standard .docx report | Finance tab → Report button, or Settings → Export → Quick Exports |
| Custom .docx | Settings → Export → Custom Report Builder (choose sections + divisions) |
| Chargeback Excel | Finance tab → Excel button; multi-sheet, one tab per division |
| Chargeback CSV | Finance tab → CSV button |
| Subscriber list CSV | Subscribers tab → CSV button |

---

## Webhooks

After each bill import TelecomLens POSTs JSON to configured URLs:
```json
{
  "event": "bill.imported",
  "org_id": "z0000605",
  "bill_id": 1,
  "statement_date": "01/05/2026",
  "account_total": 1087536.49,
  "subscriber_count": 1470
}
```
Configure in **Settings → Webhooks**. Optional HMAC-SHA256 signing via `X-TelecomLens-Signature`.

---

## API

Interactive docs: **http://localhost:8000/docs**

Key endpoints:

| Endpoint | Purpose |
|----------|---------|
| `POST /api/bills/upload` | Import a PDF bill |
| `GET /api/bills/{id}/summary` | Bill totals (spend, taxes, outstanding) |
| `GET /api/bills/{id}/drilldown` | Line items for any field/value |
| `GET /api/orgs/{id}/subscribers/{num}/history` | Cross-bill history for one number (optional `as_of`) |
| `GET /api/number-search` | Find a number across all bills/orgs (Trace tab) |
| `GET /api/orgs/{id}/waste` | Billed-but-unused, top increases, drop-offs |
| `POST /api/orgs/{id}/retag` | Bulk-reassign divisions |
| `GET /api/orgs/{id}/changes` | Change log |
| `POST /api/orgs/{id}/changes/{id}/rollback` | Undo a single change |
| `POST /api/orgs/{id}/changes/rollback-bulk` | Undo multiple changes |
| `GET /api/orgs/{id}/divisions` | Division registry |
| `PATCH /api/orgs/{id}/divisions/{id}` | Rename / recolour a division |
| `GET /api/orgs/{id}/budget-vs-actual` | Budget vs actual per period |
| `GET /api/orgs/{id}/forecast` | 3-month spend forecast |
| `GET /api/orgs/{id}/audit-log` | Audit trail |
| `POST /api/shutdown` | Graceful server stop |

---

## Project structure

```
telecomlens/
├── main.py              FastAPI app — all DB models, endpoints, migration + backfill
├── parser.py            PDF → structured invoice data (calibrated to real bills)
├── discover.py          Subscriber name classification helpers (ReDoS-guarded)
├── msisdn.py            Canonical Kenyan/Safaricom number normalisation
├── report.py            .docx report generator (python-docx)
├── requirements.txt     Python dependencies
├── .gitattributes       Enforces CRLF on .bat, LF on .sh/source
├── install.bat / .sh    One-shot installer (Windows / Linux+macOS)
├── start.bat / .sh      Server launcher
├── bills/               Drop PDFs here for batch import
├── tests/               Unit + integration tests
└── static/
    └── index.html       Single-file SPA dashboard (~100 KB)
```

---

## Multi-carrier support

| Carrier | Parser |
|---------|--------|
| Safaricom | Full |
| Airtel Kenya | Basic (beta) |
| Telkom Kenya | Basic (beta) |
| Faiba / JTL | Experimental |

---

## Contributing

See `CONTRIBUTING.md`. Quick checklist before a PR:
```bash
python3 -m py_compile main.py parser.py discover.py msisdn.py report.py
node --check static/index.html  # or extract the <script> block
python tests/test_msisdn.py     # unit tests
python tests/test_backfill.py   # migration + backfill
python tests/test_history.py    # history endpoint
python tests/test_insights.py   # as_of, waste, rollback, report
python tests/test_trace.py      # cross-bill number search
```

---

## License

MIT — see `LICENSE`.
