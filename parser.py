"""
parser.py — Safaricom postpay bill parser (calibrated against real bills).

Bill structure (confirmed from live bill cust_Z0000605_20260401.pdf):
  - Pages separated by form-feed (\\f)
  - First pages: account statement / transaction ledger
  - One TAX INVOICE SUMMARY page listing all invoices with Net/VAT/Excise/Billed
  - Many TAX INVOICE pages (one per subscriber line), each containing:
      Right column: Customer Number, Tariff Plan, Invoice Number, Subscriber Number
      Left column:  Subscriber name (on the Invoice Number line), address below
      Body:         Charge lines, then Amount Excluding VAT, EXCISE-15%, VAT-16%, Amount Due
  - ITEMISED BILL pages (call/data records) — these follow their TAX INVOICE page

Classification signals (priority order):
  1. User rules    2. Name keywords    3. Tariff keywords
  4. Block text    5. CDR mix          6. Tariff normalisation
  7. Spend tier fallback
"""
import re
from typing import Optional
from collections import Counter

# ── Name-based division rules ────────────────────────────────────────────────
NAME_RULES = [
    (r"SECURITY|GUARD|ALARM|CCTV|PATROL|WATCHMAN",           "Security"),
    (r"\bICT\b|TECH|SYSTEM|SERVER|NETWORK|\bIT\b|HELPDESK",  "ICT"),
    (r"OPERATIONS|OPS\b|OPERAT|FIELD|FLEET",                  "Operations"),
    (r"FINANCE|ACCOUNT|AUDIT|TAX\b|PAYABLE|TREASURY",         "Finance"),
    (r"\bHR\b|HUMAN.?RES|PERSONNEL|STAFF|TALENT",             "HR"),
    (r"EXEC|DIRECTOR|\bCEO\b|\bMD\b|C[FIO]O\b|\bHEAD\b|BOARD", "Executive"),
    (r"SALES|MARKET|COMMERC|BUSINESS.?DEV|\bBD\b",            "Sales & Marketing"),
    (r"LOGISTICS|SUPPLY|WAREHOUSE|PROCURE|STORES|DRIVER",     "Logistics"),
    (r"LEGAL|COMPLIANCE|RISK|GOVERNANCE",                     "Legal & Compliance"),
    (r"ADMIN|RECEPTION|OFFICE|REGISTRY|POOL\b",               "Administration"),
    (r"MANAGER|SUPERVISOR|COORD|LEAD\b",                      "Management"),
    (r"CUSTOMER.?SERVICE|CALL.?CENT|SUPPORT\b|CARE\b",        "Customer Service"),
    (r"ENGINEER|MAINT|REPAIR|WORKSHOP|PLANT",                 "Engineering"),
    (r"PROJECT|PROGRAM|PMO\b",                                "Projects"),
    (r"RESEARCH|R&D\b|INNOVATION|\bLAB\b",                    "R&D"),
    (r"TRAINING|LEARNING|CAPACITY|ACADEMY",                   "Training"),
    (r"MEDIA|COMMS?\b|\bPR\b|PUBLIC.?REL|CORPORATE.?COM",    "Communications"),
    (r"FIBER|FIXED.?DATA|IP.?LINK|CLOUD\b|5G\b|MPLS|LEASED", "Fixed Data"),
    (r"DATA.?SIM|MODEM|DONGLE|MIFI|ROUTER|\bM2M\b|\bIOT\b",  "Mobile Data"),
    (r"GSM|HANDSET|PHONE|VOICE\b",                            "GSM Handsets"),
]

# ── Tariff-based rules ────────────────────────────────────────────────────────
TARIFF_RULES = [
    (r"FIBER|FIBRE|FTTH|FTTB|HOME.?FIBRE|BIZ.?FIBRE|LEASED|MPLS|IP.?VPN|DEDICATED",
     "Fixed Data & Fibre"),
    (r"M2M|DATA\s*CARD|DATA\s*BUNDLE|MIFI|DONGLE|MODEM|ROUTER|IOT|JASPER|100MB|500MB|1GB|5GB",
     "Mobile Data / SIM"),
    (r"CORPORATE|ENTERPRISE|\bBIZ\b|BIASHARA|BUSINESS.?(COMPLETE|PLUS|MAX|ELITE|ADVANCE|POST)",
     "Corporate Voice"),
    (r"CORPORATEPOSTPAY|ADVANTAGE.?POSTPAY|POSTPAY|POSTPAID|STAWI|PESA.?PAY|LIPA\b|TALKMORE",
     "Postpay Voice"),
    (r"PLATINUM|GOLD|DIAMOND|\bVIP\b|PREMIUM|EXECUTIVE",
     "Executive Lines"),
    (r"\bVAS\b|SUBSCRIPTION|RINGBACK|CONTENT|SKIZA|BONGA",
     "VAS & Subscriptions"),
    (r"\bSMS\b|BULK.?SMS|MESSAGING|SHORT.?CODE",
     "SMS & Messaging"),
    (r"SPONSORED|SPONSOR|CUG",
     "Sponsored / CUG Lines"),
]

# ── Invoice block text rules ─────────────────────────────────────────────────
BLOCK_RULES = [
    (r"FIXED\s+DATA|DEDICATED\s+INTERNET|FIBER|LEASED\s+LINE",  "Fixed Data & Fibre"),
    (r"M2M\d+MB|DATA\s+CARD|MOBILE\s+DATA",                     "Mobile Data / SIM"),
    (r"AIRTIME|VOICE\s+CHARGES|CALL\s+CHARGES|TALKMORE",        "Voice Lines"),
    (r"DATA\s+USAGE|DATA\s+CHARGES|INTERNET\s+CHARGES",         "Data Lines"),
    (r"ROAMING\s+CHARGES|INTERNATIONAL\s+ROAMING",              "Roaming"),
    (r"SHORT\s+CODE|PREMIUM\s+RATE|M-?PESA.*TARIFF",           "Premium & M-Pesa"),
]

# ── Geography rules ───────────────────────────────────────────────────────────
GEO_RULES = [
    (r"NAIROBI|NBI\b|WESTLAND|KILIMANI|KAREN|LANG'?ATA|INDUSTRIAL|JAMHURI", "Nairobi"),
    (r"MOMBASA|MSA\b|COAST\b|MALINDI|LAMU|KILIFI|KWALE",                    "Coast"),
    (r"KISUMU|NYANZA|WESTERN\b|KAKAMEGA|BUNGOMA|BUSIA",                     "Western"),
    (r"NAKURU|RIFT.?VALLEY|ELDORET|KERICHO|NAIVASHA",                       "Rift Valley"),
    (r"THIKA|KIAMBU|CENTRAL\b|NYERI|MURANG'?A|GATUNDU",                     "Central"),
    (r"EMBU|MERU\b|EASTERN\b|MACHAKOS|KITUI|MAKUENI",                       "Eastern"),
    (r"GARISSA|NFD\b|NORTH.?EASTERN|WAJIR|MANDERA|MARSABIT",                "North Eastern"),
]

# Precompiled CDR pattern
CDR_PAT = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})\s+"
    r"(\S+)\s+"
    r"(\d+:\d{2}:\d{2}|\d+\.\d+\s*\w+)\s+"
    r"(\d+\.\d+)\s+"
    r"([\d,]+\.\d{2})"
)

# ─────────────────────────────────────────────────────────────────────────────
# MULTI-SIGNAL CLASSIFIER
# ─────────────────────────────────────────────────────────────────────────────

def classify_line(
    raw_name: str = "",
    tariff_plan: str = "",
    cdrs: list | None = None,
    block_text: str = "",
    amount_due: float = 0,
    user_rules: list | None = None,
) -> str:
    name_u = raw_name.upper().strip()
    tar_u  = tariff_plan.upper().strip()
    blk_u  = block_text.upper()

    if user_rules:
        combined = f"{name_u} | {tar_u}"
        for pattern, division in user_rules:
            try:
                if re.search(pattern, combined):
                    return division
            except re.error:
                pass

    for pattern, division in NAME_RULES:
        if re.search(pattern, name_u):
            return division

    for pattern, division in TARIFF_RULES:
        if re.search(pattern, tar_u):
            return division

    for pattern, division in BLOCK_RULES:
        if re.search(pattern, blk_u):
            return division

    if cdrs:
        mix = _analyse_cdr_mix(cdrs)
        if mix:
            return mix

    if tar_u:
        norm = _normalise_tariff(tar_u)
        if norm:
            return norm

    if amount_due > 20000:
        return "High-Spend Lines"
    elif amount_due > 5000:
        return "Mid-Spend Lines"
    elif amount_due > 0:
        return "Standard Lines"

    return "Other / Unclassified"


def _analyse_cdr_mix(cdrs: list) -> str:
    svc: Counter = Counter(c.get("service_type", "Voice") for c in cdrs)
    total = sum(svc.values())
    if not total:
        return ""
    data_pct  = svc.get("Data", 0)  / total * 100
    voice_pct = (svc.get("Voice", 0) + svc.get("Voice_OnNet", 0)) / total * 100
    sms_pct   = svc.get("SMS", 0)   / total * 100
    vas_pct   = svc.get("VAS", 0)   / total * 100
    if data_pct  > 70: return "Data-Heavy Lines"
    if voice_pct > 80: return "Voice-Heavy Lines"
    if sms_pct   > 50: return "SMS-Heavy Lines"
    if vas_pct   > 40: return "VAS & Subscriptions"
    if data_pct > 30 and voice_pct > 30: return "Voice + Data Lines"
    return ""


def _normalise_tariff(tariff_upper: str) -> str:
    cleaned = re.sub(r"\s*\d{3,}$", "", tariff_upper).strip()
    cleaned = re.sub(r"\s*KES\s*\d+.*$", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\s*[-_/]+\s*$", "", cleaned).strip()
    if not cleaned or len(cleaned) < 3:
        return ""
    return cleaned.title()


# Backward-compat wrapper
def classify_name(name: str, user_rules: list | None = None) -> str:
    return classify_line(raw_name=name, user_rules=user_rules)


def classify_geo(name: str) -> str:
    n = name.upper()
    for pattern, region in GEO_RULES:
        if re.search(pattern, n):
            return region
    return "Other"


# ─────────────────────────────────────────────────────────────────────────────
# BILL PARSER  (rewritten against actual Safaricom bill format)
# ─────────────────────────────────────────────────────────────────────────────

def parse_bill(text: str, user_rules: list | None = None) -> dict:
    """
    Parse a Safaricom postpay bill PDF (converted with pdftotext -layout).
    Returns a dict with org metadata and a list of per-subscriber invoices.
    """
    pages = text.split('\f')

    # ── Extract org-level fields from first page ───────────────────────────
    first_page = pages[0] if pages else ""
    org_name, org_account, statement_date, outstanding = _parse_header(first_page)

    # ── Extract grand totals from TAX INVOICE SUMMARY ─────────────────────
    # Pass full text so _parse_summary_totals can find TAX ANALYSIS anywhere
    account_total, total_net, total_vat, total_excise = _parse_summary_totals(text)

    # ── Parse each TAX INVOICE page ────────────────────────────────────────
    # Filter: must contain 'TAX INVOICE', not SUMMARY, not ITEMISED BILL
    inv_pages = [
        p for p in pages
        if 'TAX INVOICE' in p
        and 'TAX INVOICE SUMMARY' not in p
        and 'ITEMISED BILL' not in p
    ]

    invoices = []
    seen_inv_nums: set[str] = set()
    for page in inv_pages:
        inv = _parse_invoice_page(page, user_rules)
        if inv and inv["invoice_number"] not in seen_inv_nums:
            seen_inv_nums.add(inv["invoice_number"])
            invoices.append(inv)

    return {
        "org_name":      org_name,
        "org_account":   org_account,
        "statement_date": statement_date,
        "account_total": account_total,
        "outstanding":   outstanding,
        "total_net":     total_net,
        "total_vat":     total_vat,
        "total_excise":  total_excise,
        "invoices":      invoices,
    }


def _parse_header(page: str) -> tuple[str, str, str, float]:
    """Extract org name, customer number, statement date, outstanding from first page."""
    org_name = ""
    org_account = ""
    statement_date = ""
    outstanding = 0.0

    for line in page.splitlines():
        s = line.strip()
        if not s:
            continue

        # Customer Number (right-justified field)
        if not org_account:
            m = re.search(r'Customer Number\s+([A-Z0-9]+)', line)
            if m:
                org_account = m.group(1)

        # Statement Date
        if not statement_date:
            m = re.search(r'Statement Date\s+(\d{1,2}/\d{2}/\d{4})', line)
            if m:
                statement_date = m.group(1)

        # Outstanding (bill-level)
        if not outstanding:
            m = re.search(r'Amount Outstanding\s+Ksh\s+([\d,]+\.\d{2})', line, re.I)
            if m:
                outstanding = float(m.group(1).replace(',', ''))

        # Org name: indented 3 spaces, not a header/address/footer line
        if not org_name and re.match(r'^\s{1,6}[A-Z][A-Za-z]', line):
            candidate = s
            skip_terms = {'POSTPAY BILL', 'P.O BOX', 'P.O. BOX', 'NAIROBI',
                          'KENYA', 'POLO', 'SAFARICOM', 'WWW.', 'PAGE ', 'PAY '}
            if not any(term in candidate.upper() for term in skip_terms):
                if len(candidate) > 3 and not re.match(r'^\d', candidate):
                    org_name = candidate

    return org_name, org_account, statement_date, outstanding


def _parse_summary_totals(full_text: str) -> tuple[float, float, float, float]:
    """
    Extract grand totals from the TAX ANALYSIS section.
    The TAX ANALYSIS page contains:
      Net Amount                           840,316.10
      VAT                       16%        150,002.92
      Excise Duty               15%         97,217.47
      Gross Amount                       1,087,536.49
    Also: Total Invoiced line, and a 4-column totals row in the summary list.
    Searches the full bill text to find these anywhere.
    """
    total_billed = 0.0
    total_net    = 0.0
    total_vat    = 0.0
    total_excise = 0.0

    # Primary: TAX ANALYSIS labeled lines (most reliable)
    m = re.search(r'Net Amount\s+([\d,]+\.\d{2})', full_text)
    if m:
        total_net = float(m.group(1).replace(',', ''))
    m = re.search(r'VAT\s+16%\s+([\d,]+\.\d{2})', full_text)
    if m:
        total_vat = float(m.group(1).replace(',', ''))
    m = re.search(r'Excise Duty\s+15%\s+([\d,]+\.\d{2})', full_text)
    if m:
        total_excise = float(m.group(1).replace(',', ''))
    m = re.search(r'Gross Amount\s+([\d,]+\.\d{2})', full_text)
    if m:
        total_billed = float(m.group(1).replace(',', ''))

    # Secondary: "Total Invoiced" line
    if not total_billed:
        m = re.search(r'Total\s+Invoiced\s+([\d,]+\.\d{2})', full_text)
        if m:
            total_billed = float(m.group(1).replace(',', ''))

    # Tertiary: last 4-column totals row in the summary list
    # (840,316.10   150,002.92   97,217.47   1,087,536.49)
    if not total_billed:
        for line in reversed(full_text.splitlines()):
            nums = re.findall(r'[\d,]+\.\d{2}', line)
            if len(nums) == 4:
                try:
                    n = float(nums[0].replace(',', ''))
                    v = float(nums[1].replace(',', ''))
                    e = float(nums[2].replace(',', ''))
                    b = float(nums[3].replace(',', ''))
                    if b > 10000:   # sanity: grand total must be substantial
                        total_net    = n
                        total_vat    = v
                        total_excise = e
                        total_billed = b
                        break
                except ValueError:
                    pass

    return total_billed, total_net, total_vat, total_excise


def _parse_invoice_page(page: str, user_rules) -> Optional[dict]:
    """
    Parse a single TAX INVOICE page.

    Right-column fields (pattern: LABEL  <spaces>  VALUE):
      Customer Number, Tariff Plan, Invoice Date, Invoice Number, Subscriber Number

    Left-column:
      Subscriber name appears on the SAME LINE as "Invoice Number" in the right column.
      The name is the text before the large whitespace gap.

    Financial fields (right-justified, Ksh on Amount Due line):
      Amount Excluding VAT and Excise Duty  <spaces>  <amount>
      EXCISE - 15%                          <spaces>  <amount>
      VAT - 16%                             <spaces>  <amount>
      Amount Due                            <spaces>  Ksh   <amount>
    """
    inv_num = sub_num = raw_name = tariff = ""
    pre_tax = excise = vat = amount_due = 0.0

    lines = page.splitlines()

    for line in lines:
        # Invoice Number (also contains subscriber name on left)
        if not inv_num:
            m = re.search(r'Invoice Number\s+(B\d+-\d+)', line)
            if m:
                inv_num = m.group(1)
                # Subscriber name = left portion before large whitespace gap
                left = line[:m.start()].strip()
                if left and len(left) > 1:
                    raw_name = left

        # Subscriber Number
        if not sub_num:
            m = re.search(r'Subscriber Number\s+(\d{9,12})', line)
            if m:
                sub_num = m.group(1)

        # Tariff Plan — value is everything after "Tariff Plan" + spaces
        if not tariff:
            m = re.search(r'Tariff Plan\s{2,}(.+)', line)
            if m:
                tariff = m.group(1).strip()

        # Amount Excluding VAT and Excise Duty
        if not pre_tax:
            m = re.search(r'Amount Excluding VAT and Excise Duty\s+([\d,]+\.\d{2})', line)
            if m:
                pre_tax = float(m.group(1).replace(',', ''))

        # EXCISE - 15%
        if not excise:
            m = re.search(r'EXCISE\s*-\s*15%\s+([\d,]+\.\d{2})', line)
            if m:
                excise = float(m.group(1).replace(',', ''))

        # VAT - 16%
        if not vat:
            m = re.search(r'VAT\s*-\s*16%\s+([\d,]+\.\d{2})', line)
            if m:
                vat = float(m.group(1).replace(',', ''))

        # Amount Due (has "Ksh" as a column separator)
        if not amount_due:
            m = re.search(r'Amount Due\s+Ksh\s+([\d,]+\.\d{2})', line)
            if m:
                amount_due = float(m.group(1).replace(',', ''))

    if not inv_num and not sub_num:
        return None

    # Parse CDRs from ITEMISED lines in the same page (sometimes included)
    cdrs = _parse_cdrs(page)

    division = classify_line(
        raw_name=raw_name,
        tariff_plan=tariff,
        cdrs=cdrs,
        block_text=page[:3000],
        amount_due=amount_due,
        user_rules=user_rules,
    )

    return {
        "invoice_number":    inv_num,
        "subscriber_number": sub_num,
        "raw_name":          raw_name,
        "tariff_plan":       tariff,
        "division":          division,
        "geography":         classify_geo(raw_name),
        "pre_tax":           pre_tax,
        "excise":            excise,
        "vat":               vat,
        "amount_due_kes":    amount_due,
        "outstanding":       0.0,   # outstanding is bill-level, not per-invoice
        "cdr_count":         len(cdrs),
        "cdr_records":       cdrs,
        "sponsored_lines":   [],
    }


def _parse_cdrs(page: str) -> list[dict]:
    """Extract CDR records from itemised sections of the page."""
    cdrs = []
    for line in page.splitlines():
        m = CDR_PAT.search(line)
        if m:
            cdrs.append({
                "date":         m.group(1),
                "time":         m.group(2),
                "destination":  m.group(3),
                "duration":     m.group(4).strip(),
                "rate":         float(m.group(5)),
                "charge":       float(m.group(6).replace(',', '')),
                "service_type": _infer_service(line),
            })
    return cdrs


def _infer_service(line: str) -> str:
    u = line.upper()
    if "DATA" in u or "MB" in u or "GB" in u:
        return "Data"
    if "SMS" in u:
        return "SMS"
    if "VAS" in u or "SUBSCRIPTION" in u:
        return "VAS"
    if "ONNET" in u or "ON-NET" in u or "ON NET" in u:
        return "Voice_OnNet"
    return "Voice"
