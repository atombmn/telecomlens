"""
parser.py — Org-agnostic Safaricom postpay bill parser.
Extracts subscriber invoices, CDR records, and account totals from pdftotext -layout output.
"""
import re
from typing import Optional

DIVISION_RULES = [
    (r"SECURITY|GUARD|ALARM|CCTV|PATROL",      "Security"),
    (r"ICT|TECH|SYSTEM|SERVER|NETWORK|IT\b",   "ICT"),
    (r"OPERATIONS|OPS\b|OPERAT",               "Operations"),
    (r"FINANCE|ACCOUNT|AUDIT|TAX|PAYABLE",     "Finance"),
    (r"HR\b|HUMAN.?RES|PERSONNEL|STAFF",       "HR"),
    (r"EXEC|DIRECTOR|CEO|MD\b|MANAGER|HEAD\b", "Executive"),
    (r"SALES|MARKET|COMMERC|BUSINESS.?DEV",    "Sales"),
    (r"LOGISTICS|SUPPLY|WAREHOUSE|PROCURE",    "Logistics"),
    (r"LEGAL|COMPLIANCE|RISK|GOVERNANCE",      "Legal"),
    (r"FIBER|FIXED.?DATA|IP.?LINK|CLOUD|5G",  "Fixed Data"),
    (r"MOBILE.?DATA|DATA.?SIM|MODEM",         "Mobile Data"),
    (r"GSM|HANDSET|PHONE|VOICE\b",            "GSM Handsets"),
]

GEO_RULES = [
    (r"NAIROBI|NBI\b|WESTLAND|KILIMANI",       "Nairobi"),
    (r"MOMBASA|MSA\b|COAST",                   "Coast"),
    (r"KISUMU|NYANZA|WESTERN",                 "Western"),
    (r"NAKURU|RIFT.?VALLEY|ELDORET",           "Rift Valley"),
    (r"THIKA|KIAMBU|CENTRAL",                  "Central"),
    (r"EMBU|MERU|EASTERN",                     "Eastern"),
    (r"GARISSA|NFD\b|NORTH.?EASTERN",          "North Eastern"),
]

CDR_PAT = re.compile(
    r"(\d{2}/\d{2}/\d{4})\s+(\d{2}:\d{2}:\d{2})\s+"
    r"(\S+)\s+"
    r"(\d+:\d{2}:\d{2}|\d+\.\d+\s*\w+)\s+"
    r"(\d+\.\d+)\s+"
    r"([\d,]+\.\d{2})"
)


def classify_name(name: str, user_rules: list[tuple[str, str]] | None = None) -> str:
    n = name.upper()
    if user_rules:
        for pattern, division in user_rules:
            try:
                if re.search(pattern, n):
                    return division
            except re.error:
                pass
    for pattern, division in DIVISION_RULES:
        if re.search(pattern, n):
            return division
    return "Unclassified"


def classify_geo(name: str) -> str:
    n = name.upper()
    for pattern, region in GEO_RULES:
        if re.search(pattern, n):
            return region
    return "Other"


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

    return {
        "invoice_number": inv_num,
        "subscriber_number": sub_num,
        "raw_name": raw_name,
        "tariff_plan": tariff,
        "division": classify_name(raw_name, user_rules),
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
