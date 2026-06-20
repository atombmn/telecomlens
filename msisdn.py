"""
msisdn.py — canonical normalisation of Kenyan / Safaricom subscriber numbers.

Why this exists
---------------
Across bills the same physical line can be printed in several formats:

    0722123456   254722123456   +254 722 123 456   254-722-123456

The rest of TelecomLens currently matches subscriber numbers with exact string
equality (e.g. `InvoiceLine.subscriber_number == search.strip()`) and keys the
lifecycle diff on the raw value. Any format drift therefore splits one line's
history into two and produces phantom "deactivation + new activation" events.

This module gives a single canonical key so a number means the same thing in
every bill, query, and timeline.

Canonical form
--------------
The 12-digit international form, no '+':

    2547XXXXXXXX   or   2541XXXXXXXX

Design rules
------------
* Idempotent: normalise_msisdn(normalise_msisdn(x)) == normalise_msisdn(x)
* Conservative: anything that is not a recognisable Kenyan mobile number is
  returned cleaned (whitespace-stripped) but otherwise UNCHANGED, so fixed
  lines (020…), data-only identifiers, account refs, or foreign numbers are
  never corrupted into a fake mobile number.
* Dependency-free (stdlib only) — adds nothing to requirements.txt.
"""

import re

__all__ = ["normalise_msisdn", "display_msisdn"]

_NON_DIGITS = re.compile(r"\D+")


def normalise_msisdn(raw) -> str:
    """Return the canonical 254XXXXXXXXX form, or the cleaned input if it is
    not a recognisable Kenyan mobile number."""
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s:
        return ""

    digits = _NON_DIGITS.sub("", s)
    if not digits:
        return s  # purely a label, e.g. "SIM" — leave untouched

    # 2547XXXXXXXX / 2541XXXXXXXX  (already canonical, 12 digits)
    if len(digits) == 12 and digits.startswith("254") and digits[3] in "71":
        return digits

    # 07XXXXXXXX / 01XXXXXXXX  (local, 10 digits, leading 0)
    if len(digits) == 10 and digits.startswith("0") and digits[1] in "71":
        return "254" + digits[1:]

    # 7XXXXXXXX / 1XXXXXXXX  (9 digits, no prefix at all)
    if len(digits) == 9 and digits[0] in "71":
        return "254" + digits

    # 2540722…  (double prefix: 254 + local-with-0, 13 digits) — seen in some exports
    if len(digits) == 13 and digits.startswith("2540") and digits[4] in "71":
        return "254" + digits[4:]

    # Not a KE mobile pattern — do not guess, return cleaned original.
    return s


def display_msisdn(canonical) -> str:
    """Render a canonical 254… number in friendly local 0… form for the UI.
    Non-canonical input is returned unchanged."""
    c = (canonical or "").strip()
    if len(c) == 12 and c.startswith("254") and c[3] in "71":
        return "0" + c[3:]
    return c
