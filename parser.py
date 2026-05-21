"""
parser.py — Org-agnostic Safaricom postpay bill parser.
Extracts subscriber invoices, CDR records, and account totals from pdftotext -layout output.

Classification strategy (applied in priority order):
  1. User-defined mapping rules (regex on name) — highest priority
  2. Organisational keyword match on subscriber name
  3. Tariff plan keyword match (infer line type from plan name)
  4. CDR service-mix analysis (voice-heavy vs data-heavy)
  5. Charge component keywords from invoice block text
  6. Fallback to normalised tariff plan name as category
  7. Spend-tier bucketing (High / Mid / Low)
"""
import re
from typing import Optional
from collections import Counter


# ── Name-based rules — match keywords in the subscriber name ─────────────────
NAME_RULES = [
    (r"SECURITY|GUARD|ALARM|CCTV|PATROL",                "Security"),
    (r"ICT|TECH|SYSTEM|SERVER|NETWORK|IT\b|HELPDESK",    "ICT"),
    (r"OPERATIONS|OPS\b|OPERAT|FIELD|FLEET",             "Operations"),
    (r"FINANCE|ACCOUNT|AUDIT|TAX|PAYABLE|TREASURY",      "Finance"),
    (r"HR\b|HUMAN.?RES|PERSONNEL|STAFF|TALENT",          "HR"),
    (r"EXEC|DIRECTOR|CEO|MD\b|C[FIO]O\b|HEAD\b|BOARD",  "Executive"),
    (r"SALES|MARKET|COMMERC|BUSINESS.?DEV|BD\b",         "Sales & Marketing"),
    (r"LOGISTICS|SUPPLY|WAREHOUSE|PROCURE|STORES",        "Logistics"),
    (r"LEGAL|COMPLIANCE|RISK|GOVERNANCE",                 "Legal & Compliance"),
    (r"ADMIN|RECEPTION|OFFICE|REGISTRY|DRIVER|POOL",      "Administration"),
    (r"MANAGER|SUPERVISOR|COORD|LEAD\b",                  "Management"),
    (r"CUSTOMER.?SERVICE|CALL.?CENT|SUPPORT|CARE",        "Customer Service"),
    (r"ENGINEER|MAINT|REPAIR|WORKSHOP|PLANT",             "Engineering"),
    (r"PROJECT|PROGRAM|PMO\b",                            "Projects"),
    (r"RESEARCH|R&D\b|INNOVATION|LAB\b",                  "R&D"),
    (r"TRAINING|LEARNING|CAPACITY|ACADEMY",               "Training"),
    (r"MEDIA|COMMS?\b|PR\b|PUBLIC.?REL|CORPORATE.?COM",   "Communications"),
    (r"FIBER|FIXED.?DATA|IP.?LINK|CLOUD|5G|MPLS|LEASED", "Fixed Data"),
    (r"DATA.?SIM|MODEM|DONGLE|MIFI|ROUTER|M2M|IOT",      "Mobile Data"),
    (r"GSM|HANDSET|PHONE|VOICE\b",                        "GSM Handsets"),
]

# ── Tariff-based rules — match keywords in the tariff plan name ───────────────
TARIFF_RULES = [
    # Fixed / fibre
    (r"FIBER|FIBRE|FTTH|FTTB|HOME.?FIBRE|BIZ.?FIBRE|LEASED|MPLS|IP.?VPN|DEDICATED",
     "Fixed Data & Fibre"),
    # Data SIMs / modems
    (r"DATA\s*(?:PLAN|SIM|ONLY|BUNDLE)|MOBILE.?WIFI|MIFI|DONGLE|MODEM|ROUTER|M2M|IOT|JASPER",
     "Mobile Data / Modem"),
    # Enterprise voice bundles
    (r"CORPORATE|ENTERPRISE|BIZ\b|BIASHARA|BUSINESS.?(?:COMPLETE|PLUS|MAX|ELITE|ADVANCE)",
     "Corporate Voice"),
    # Standard postpay voice
    (r"POST.?PAY|POSTPAID|STAWI|PESA.?PAY|LIPA\b|OKOA",
     "Postpay Voice"),
    # High-value plans (by name)
    (r"PLATINUM|GOLD|DIAMOND|VIP|PREMIUM|EXECUTIVE",
     "Executive Lines"),
    # VAS / subscriptions
    (r"VAS|SUBSCRIPTION|RINGBACK|CONTENT|SKIZA|BONGA",
     "VAS & Subscriptions"),
    # SMS-heavy
    (r"SMS|BULK\s*SMS|MESSAGING|SHORT.?CODE",
     "SMS & Messaging"),
]

# ── Block-text rules — match keywords in the full invoice block ───────────────
BLOCK_RULES = [
    (r"FIXED\s+DATA|DEDICATED\s+INTERNET|FIBER|LEASED\s+LINE",  "Fixed Data & Fibre"),
    (r"AIRTIME\s+CHARGES|VOICE\s+CHARGES|CALL\s+CHARGES",       "Voice Lines"),
    (r"DATA\s+USAGE|DATA\s+CHARGES|INTERNET\s+CHARGES",         "Data Lines"),
    (r"ROAMING\s+CHARGES|INTERNATIONAL\s+ROAMING",               "Roaming"),
    (r"SHORT\s+CODE|PREMIUM\s+RATE|M-?PESA.*TARIFF",             "Premium & M-Pesa"),
]

# ── Geography rules ───────────────────────────────────────────────────────────
GEO_RULES = [
    (r"NAIROBI|NBI\b|WESTLAND|KILIMANI|KAREN|LANG'?ATA|INDUSTRIAL",  "Nairobi"),
    (r"MOMBASA|MSA\b|COAST|MALINDI|LAMU|KILIFI|KWALE",               "Coast"),
    (r"KISUMU|NYANZA|WESTERN|KAKAMEGA|BUNGOMA|BUSIA",                 "Western"),
    (r"NAKURU|RIFT.?VALLEY|ELDORET|KERICHO|NAIVASHA|NYANDARUA",      "Rift Valley"),
    (r"THIKA|KIAMBU|CENTRAL|NYERI|MURANG'?A|GATUNDU",                "Central"),
    (r"EMBU|MERU|EASTERN|MACHAKOS|KITUI|MAKUENI",                    "Eastern"),
    (r"GARISSA|NFD\b|NORTH.?EASTERN|WAJIR|MANDERA|MARSABIT",         "North Eastern"),
]

CDR_PAT = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})\s+"
    r"(\S+)\s+"
    r"(\d+:\d{2}:\d{2}|\d+\.\d+\s*\w+)\s+"
    r"(\d+\.\d+)\s+"
    r"([\d,]+\.\d{2})"
)


# ═══════════════════════════════════════════════════════════════════════════════
# MULTI-SIGNAL CLASSIFIER
# ═══════════════════════════════════════════════════════════════════════════════

def classify_line(
    raw_name: str = "",
    tariff_plan: str = "",
    cdrs: list[dict] | None = None,
    block_text: str = "",
    amount_due: float = 0,
    user_rules: list[tuple[str, str]] | None = None,
) -> str:
    """
    Classify a subscriber line using every available signal.
    Returns the most specific division/category string.
    """

    name_upper = raw_name.upper().strip()
    tariff_upper = tariff_plan.upper().strip()
    block_upper = block_text.upper()

    # ── Priority 1: User-defined rules (regex on name + tariff) ──────────
    if user_rules:
        combined = f"{name_upper} | {tariff_upper}"
        for pattern, division in user_rules:
            try:
                if re.search(pattern, combined):
                    return division
            except re.error:
                pass

    # ── Priority 2: Organisational keyword in subscriber name ────────────
    for pattern, division in NAME_RULES:
        if re.search(pattern, name_upper):
            return division

    # ── Priority 3: Tariff plan keyword match ────────────────────────────
    if tariff_upper:
        for pattern, division in TARIFF_RULES:
            if re.search(pattern, tariff_upper):
                return division

    # ── Priority 4: Invoice block text keywords ──────────────────────────
    if block_upper:
        for pattern, division in BLOCK_RULES:
            if re.search(pattern, block_upper):
                return division

    # ── Priority 5: CDR service-mix analysis ─────────────────────────────
    if cdrs:
        mix = _analyse_cdr_mix(cdrs)
        if mix:
            return mix

    # ── Priority 6: Normalise tariff plan as a category ──────────────────
    if tariff_upper:
        normalised = _normalise_tariff(tariff_upper)
        if normalised:
            return normalised

    # ── Priority 7: Spend-tier fallback ──────────────────────────────────
    if amount_due > 20000:
        return "High-Spend Lines"
    elif amount_due > 5000:
        return "Mid-Spend Lines"
    elif amount_due > 0:
        return "Standard Lines"

    return "Other / Unclassified"


def _analyse_cdr_mix(cdrs: list[dict]) -> str:
    """Classify based on service-type distribution of CDR records."""
    if not cdrs:
        return ""

    svc_counts: Counter = Counter()
    for cdr in cdrs:
        svc = cdr.get("service_type", "Voice")
        svc_counts[svc] += 1

    total = sum(svc_counts.values())
    if total == 0:
        return ""

    data_pct = (svc_counts.get("Data", 0) / total) * 100
    voice_pct = (svc_counts.get("Voice", 0) + svc_counts.get("Voice_OnNet", 0)) / total * 100
    sms_pct = (svc_counts.get("SMS", 0) / total) * 100
    vas_pct = (svc_counts.get("VAS", 0) / total) * 100

    # Strong signal thresholds
    if data_pct > 70:
        return "Data-Heavy Lines"
    if voice_pct > 80:
        return "Voice-Heavy Lines"
    if sms_pct > 50:
        return "SMS-Heavy Lines"
    if vas_pct > 40:
        return "VAS & Subscriptions"

    # Mixed usage
    if data_pct > 30 and voice_pct > 30:
        return "Voice + Data Lines"

    return ""


def _normalise_tariff(tariff_upper: str) -> str:
    """Extract a clean category from the tariff plan name."""
    # Strip trailing numbers, codes, amounts
    cleaned = re.sub(r"\s*\d{3,}$", "", tariff_upper).strip()
    cleaned = re.sub(r"\s*KES\s*\d+.*$", "", cleaned, flags=re.I).strip()
    cleaned = re.sub(r"\s*[-_/]+\s*$", "", cleaned).strip()

    if not cleaned or len(cleaned) < 3:
        return ""

    # Title-case for display
    return cleaned.title()


# ── Legacy single-arg wrapper (for backward compatibility in main.py) ────────
def classify_name(name: str, user_rules: list[tuple[str, str]] | None = None) -> str:
    """Backward-compatible wrapper — name-only classification."""
    return classify_line(raw_name=name, user_rules=user_rules)


def classify_geo(name: str) -> str:
    n = name.upper()
    for pattern, region in GEO_RULES:
        if re.search(pattern, n):
            return region
    return "Other"


# ═══════════════════════════════════════════════════════════════════════════════
# BILL PARSER
# ═══════════════════════════════════════════════════════════════════════════════

def parse_bill(text: str, user_rules: list[tuple[str, str]] | None = None) -> dict:
    lines = text.splitlines()

    org_name, org_account, statement_date = "", "", ""
    for i, l in enumerate(lines[:40]):
        if not org_name and re.search(r"^[A-Z][A-Z &,.'()-]{5,}", l.strip()):
            org_name = l.strip()
        m = re.search(r"Account\s+(?:No|Number)[:\s]+(\S+)", l, re.I)
        if m:
            org_account = m.group(1)
        m = re.search(r"Statement\s+Date[:\s]+(\d{1,2}[/-]\w+[/-]\d{4}|\d{4}-\d{2}-\d{2})", l, re.I)
        if m:
            statement_date = m.group(1)

    blocks = re.split(r"(?=TAX INVOICE)", text)
    invoices = []
    for block in blocks[1:]:
        inv = _parse_invoice(block, user_rules)
        if inv:
            invoices.append(inv)

    account_total = 0.0
    m = re.search(r"Total\s+Amount\s+Due[:\s]+([\d,]+\.?\d*)", text, re.I)
    if m:
        account_total = float(m.group(1).replace(",", ""))

    return {
        "org_name": org_name,
        "org_account": org_account,
        "statement_date": statement_date,
        "account_total": account_total,
        "invoices": invoices,
    }


def _parse_invoice(block: str, user_rules) -> Optional[dict]:
    lines = block.splitlines()

    inv_num = sub_num = raw_name = tariff = ""
    pre_tax = excise = vat = amount_due = outstanding = 0.0

    for l in lines[:60]:
        m = re.search(r"Invoice\s+(?:No|Number)[:\s]+(\S+)", l, re.I)
        if m:
            inv_num = m.group(1)
        m = re.search(r"(?:Subscriber|MSISDN|Line)\s+(?:No|Number)[:\s]+([\d+]+)", l, re.I)
        if m:
            sub_num = m.group(1).lstrip("+")
        m = re.search(r"(?:Name|Subscriber\s+Name)[:\s]+(.+)", l, re.I)
        if m:
            raw_name = m.group(1).strip()
        m = re.search(r"(?:Tariff|Plan|Package)[:\s]+(.+)", l, re.I)
        if m:
            tariff = m.group(1).strip()[:80]
        m = re.search(r"(?:Pre.?Tax|Sub.?Total)[:\s]+([\d,]+\.\d{2})", l, re.I)
        if m:
            pre_tax = float(m.group(1).replace(",", ""))
        m = re.search(r"Excise[:\s]+([\d,]+\.\d{2})", l, re.I)
        if m:
            excise = float(m.group(1).replace(",", ""))
        m = re.search(r"VAT[:\s]+([\d,]+\.\d{2})", l, re.I)
        if m:
            vat = float(m.group(1).replace(",", ""))
        m = re.search(r"Amount\s+Due[:\s]+([\d,]+\.\d{2})", l, re.I)
        if m:
            amount_due = float(m.group(1).replace(",", ""))
        m = re.search(r"(?:Outstanding|B/F)[:\s]+([\d,]+\.\d{2})", l, re.I)
        if m:
            outstanding = float(m.group(1).replace(",", ""))

    if not sub_num and not inv_num:
        return None

    cdrs = []
    for l in lines:
        m = CDR_PAT.search(l)
        if m:
            charge_str = m.group(6).replace(",", "")
            svc = _infer_service(l)
            cdrs.append({
                "date": m.group(1),
                "time": m.group(2),
                "destination": m.group(3),
                "duration": m.group(4).strip(),
                "rate": float(m.group(5)),
                "charge": float(charge_str),
                "service_type": svc,
            })

    sponsored = []
    sp_block = re.search(r"Sponsored.*?(?=\n\s*\n|\Z)", block, re.S | re.I)
    if sp_block:
        for m in re.finditer(r"(\d{9,12})\s+(.+?)\s+([\d,]+\.\d{2})", sp_block.group()):
            sponsored.append({"number": m.group(1), "name": m.group(2).strip(),
                               "charge": float(m.group(3).replace(",", ""))})

    # ── Multi-signal classification ──────────────────────────────────────
    division = classify_line(
        raw_name=raw_name,
        tariff_plan=tariff,
        cdrs=cdrs,
        block_text=block[:2000],   # first 2000 chars of invoice block
        amount_due=amount_due,
        user_rules=user_rules,
    )

    return {
        "invoice_number": inv_num,
        "subscriber_number": sub_num,
        "raw_name": raw_name,
        "tariff_plan": tariff,
        "division": division,
        "geography": classify_geo(raw_name),
        "pre_tax": pre_tax,
        "excise": excise,
        "vat": vat,
        "amount_due_kes": amount_due,
        "outstanding": outstanding,
        "cdr_count": len(cdrs),
        "cdr_records": cdrs,
        "sponsored_lines": sponsored,
    }


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
