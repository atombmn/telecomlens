# Contributing to TelecomLens

Thank you for your interest in improving TelecomLens. This guide covers how to set up a development environment, the project structure, and what we look for in pull requests.

---

## Development setup

```bash
git clone https://github.com/atombmn/telecomlens.git
cd telecomlens
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install openpyxl httpx        # optional, for Excel + webhook features
```

Install `pdftotext`:
```bash
# Ubuntu / Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler

# Windows — run install.bat which downloads Poppler automatically
```

Start the server in development mode:
```bash
uvicorn main:app --reload --port 8000
```

---

## Project layout

```
main.py       — FastAPI app, all DB models, all API endpoints
parser.py     — Converts pdftotext -layout output → structured invoice dict
discover.py   — Subscriber name tokenisation and classification helpers
report.py     — .docx report generation (python-docx)
static/
  index.html  — Single-file SPA: all HTML, CSS, and JS in one file
```

### Key design decisions

- **Single HTML file**: the entire frontend is `static/index.html`. There is no build step, no node_modules, no bundler. This keeps deployment simple and lets users inspect/edit the file directly.
- **SQLite by default**: the `DATABASE_URL` env var accepts any SQLAlchemy URL, so Postgres or MySQL can be swapped in for multi-user deployments.
- **Lazy imports for heavy deps**: `python-docx` and `openpyxl` are imported inside their respective endpoints so a missing package only breaks that feature, not the whole server.

---

## Making changes

### Adding a new tab
1. Add the tab ID and label key to `renderTabs()` in `index.html`
2. Add `DEFAULT_LABELS` and `LABEL_META` entries
3. Add a handler in `renderTab(tab)` 
4. Write `renderMyTab()` and `loadMyTabData()` functions

### Adding a new API endpoint
1. Add the endpoint function to `main.py` with `@app.get/post/patch/delete`
2. Add an `AuditLog` entry for any write operation
3. Update `README.md` with the new endpoint in the API table

### Adding a new DB model
1. Define the `class` before `Base.metadata.create_all(engine)` in `main.py`
2. SQLAlchemy will auto-create the table on next startup
3. For production upgrades use Alembic migrations

### Parser changes
- `parser.py` processes raw text from `pdftotext -layout`. Test changes with a real bill by running `python3 -c "from parser import parse_bill; import sys; print(parse_bill(open(sys.argv[1]).read()))" bill.txt`
- The `DIVISION_RULES` list in `parser.py` uses `re.search` patterns applied to subscriber names — test with representative names

---

## Pre-PR checklist

```bash
# 1. Syntax check all Python files
python3 -m py_compile main.py parser.py discover.py report.py

# 2. Basic import test
python3 -c "import main"

# 3. Manual test: start server, import a bill, check all 9 tabs render
uvicorn main:app --port 8000

# 4. Check no JSON.stringify in onclick attributes
python3 -c "
import re
html = open('static/index.html').read()
bad = re.findall(r'onclick=[\"\\'][^\"\\'>]*JSON\\.stringify[^\"\\'>]*[\"\\']', html)
assert not bad, f'Unsafe onclick: {bad}'
print('XSS check passed')
"
```

---

## Reporting issues

Open a GitHub Issue with:
- TelecomLens version (see `CHANGELOG.md`)
- Python version (`python --version`)
- Operating system
- Steps to reproduce
- Error message or screenshot

---

## Licence

By contributing you agree that your contributions will be licensed under the MIT License.
