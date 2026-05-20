# 📡 TelecomLens

**TelecomLens** is a self-hosted telecom bill analytics dashboard for organisations that receive monthly postpay invoices from Safaricom (and other Kenyan carriers). It turns raw PDFs into actionable spend intelligence — division-level chargebacks, anomaly detection, budget vs actual, forecasting, subscriber lifecycle tracking, and more.

---

## Features at a glance

| Area | Capabilities |
|------|-------------|
| **Executive** | KPI cards, spend-by-division doughnut, charge components, drill-down on every cell |
| **Finance** | Tax reconciliation (Excise 15% + VAT 16%), chargeback register, GL account mapping |
| **ICT** | Subscriber search, division filter, per-line tariff and CDR count |
| **Operations** | Anomaly tracker, flagged lines with one-click drill-down |
| **Trends** | Multi-month spend trend, division stacked bars, subscriber count, top spenders |
| **Subscribers** | Registry with tags, device types, manual division remapping, lifecycle events (activations/deactivations/plan changes) |
| **Budget & Forecast** | Budget vs actual per division, 3-month linear regression forecast with confidence bands, spend alerts with threshold breach detection, cost-per-head benchmarks |
| **Reports & Export** | Custom report builder (.docx), per-division Excel chargeback pack, inline annotations, CSV export |
| **Data & Integrations** | Audit trail, outbound webhooks (with HMAC signing), multi-carrier detection |

### Drill-down everywhere
Click any KPI card, chart bar, doughnut segment, or table row to open a side panel with the exact line items, a sparkline history, top-3 contributors, and a filtered CSV export.

### Customisable labels
Every tab name, KPI card title, and section heading is editable via the ✎ Customise button — changes persist in the browser and apply throughout the dashboard including exported reports.

---

## Requirements

| Dependency | Notes |
|-----------|-------|
| Python 3.10+ | 3.13 / 3.14 fully supported |
| pdftotext (Poppler) | Bundled automatically on Windows by `install.bat` |
| pip packages | See `requirements.txt` — installed by the setup script |

---

## Quick start

### Windows
```
git clone https://github.com/atombmn/telecomlens.git
cd telecomlens
install.bat          # one-time setup: venv + packages + Poppler
start.bat            # launch server + open browser
```

### Linux / macOS
```bash
git clone https://github.com/atombmn/telecomlens.git
cd telecomlens
chmod +x install.sh start.sh
./install.sh         # one-time setup
./start.sh           # launch server + open browser
```

Then open **http://localhost:8000** and import your first PDF bill.

---

## Configuration (`.env`)

The installer creates `.env` automatically. Available settings:

```ini
DATABASE_URL=sqlite:///./telecomlens.db   # any SQLAlchemy URL
BILLS_FOLDER=bills                         # folder for batch imports
POPPLER_PATH=poppler                       # path to Poppler on Windows
CORS_ORIGINS=*                             # restrict to e.g. http://192.168.1.10:8000
```

---

## Importing bills

### Single bill
Click **⊕ Import PDF** in the top bar and choose one or more PDF files.

### Batch folder import
Place PDFs in `bills/` (or any folder), then call:
```
POST /api/bills/import-folder
Body: {"folder": "C:/bills/2026"}
```

---

## Budget & Forecast

1. Open the **Budget & Forecast** tab
2. Click **✎ Edit Budgets** to enter monthly KES budget per division, or click **⬇ CSV Template** to download a pre-filled template, fill it in Excel, and upload via **⊕ Import Budget CSV**
3. The **Budget vs Actual** view shows actual vs budget with a coloured status badge and a trend chart with a dotted budget line
4. **Spend Alerts** — set a KES ceiling per subscriber, division, or total bill. A red banner appears when the latest bill breaches any threshold
5. **Cost-per-Head** — add headcount in the budget editor to rank divisions by cost-per-employee

---

## Subscriber Management

- **Registry** — searchable list of all known lines with editable metadata (display name, division override, tags, device type, expected tariff, notes)
- **Tags** — apply custom labels (e.g. `contractor`, `executive`, `shared pool`) to individual lines or in bulk to all filtered subscribers
- **Lifecycle** — automatically detects new activations, deactivations, and tariff plan changes across consecutive bills

---

## Reports & Export

| Export | How |
|--------|-----|
| Executive .docx | Click **📄 Report** in the top bar (full standard report) |
| Custom .docx | Reports & Export tab → Report Builder (choose sections + divisions) |
| Chargeback Excel | Reports & Export tab → Excel Packs (multi-sheet, one tab per division) |
| Chargeback CSV | Click **⬇ Chargeback CSV** in the top bar |

Annotations added in the Reports & Export tab appear as footnotes in exported .docx reports.

---

## Webhooks

After each bill import, TelecomLens can POST a JSON payload to any URL:

```json
{
  "event": "bill.imported",
  "org_id": "acc001",
  "bill_id": 12,
  "statement_date": "2026-03",
  "account_total": 125000.00,
  "subscriber_count": 45
}
```

Set a shared secret in the webhook config to receive an HMAC-SHA256 signature in `X-TelecomLens-Signature: sha256=<hex>`.

Configure webhooks: **Data & Integrations → Webhooks → + Add webhook**

---

## API

Interactive API docs are available at **http://localhost:8000/docs** once the server is running.

Key endpoint groups:

| Prefix | Purpose |
|--------|---------|
| `GET /api/bills/*` | Bill data, summaries, subscribers, CDRs, drill-down |
| `GET/POST /api/orgs/{id}/budgets` | Budget management |
| `GET /api/orgs/{id}/budget-vs-actual` | Budget vs actual comparison |
| `GET /api/orgs/{id}/forecast` | 3-month spend forecast |
| `GET/POST /api/orgs/{id}/alerts` | Spend alert thresholds |
| `GET/PATCH /api/orgs/{id}/subscribers` | Subscriber profile management |
| `GET /api/orgs/{id}/lifecycle` | Activation/deactivation/plan-change events |
| `GET/POST /api/orgs/{id}/webhooks` | Webhook configuration |
| `GET /api/orgs/{id}/audit-log` | Audit trail |
| `POST /api/bills/{id}/annotations` | Inline annotations |
| `GET /api/bills/{id}/chargeback-excel.xlsx` | Per-division Excel pack |
| `POST /api/bills/{id}/report-custom.docx` | Custom report builder |

---

## Project structure

```
telecomlens/
├── main.py              FastAPI backend — all endpoints, DB models
├── parser.py            PDF text → structured invoice data
├── discover.py          Subscriber name classification helpers
├── report.py            .docx report generator (python-docx)
├── requirements.txt     Python dependencies
├── install.bat          Windows one-shot installer
├── install.sh           Linux / macOS one-shot installer
├── start.bat            Windows launcher
├── start.sh             Linux / macOS launcher
├── bills/               Drop PDFs here for batch import
└── static/
    └── index.html       Single-file SPA dashboard
```

---

## Multi-carrier support

| Carrier | Parser support |
|---------|---------------|
| Safaricom | Full |
| Airtel Kenya | Basic (beta) |
| Telkom Kenya | Basic (beta) |
| Faiba / JTL | Experimental |

Bills from multiple carriers can coexist — each gets its own organisation record with separate budget, subscriber, and trend data.

---

## Contributing

Pull requests welcome. Before submitting:
- Run `python3 -m py_compile main.py parser.py discover.py report.py`
- Test bill import and report download with a real or synthetic PDF

---

## License

MIT — see `LICENSE` for details.
