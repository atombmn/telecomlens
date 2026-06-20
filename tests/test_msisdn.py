"""Unit tests for msisdn normalisation. Run: python tests/test_msisdn.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from msisdn import normalise_msisdn, display_msisdn

CANONICAL = "254722123456"
CASES = [
    ("0722123456", CANONICAL), ("254722123456", CANONICAL),
    ("+254722123456", CANONICAL), ("+254 722 123 456", CANONICAL),
    ("254-722-123-456", CANONICAL), ("(254)722123456", CANONICAL),
    ("  0722 123 456  ", CANONICAL), ("722123456", CANONICAL),
    ("2540722123456", CANONICAL),
    ("0110000111", "254110000111"), ("254110000111", "254110000111"),
    ("0202345678", "0202345678"), ("SIM-ONLY-DATA", "SIM-ONLY-DATA"),
    ("12345", "12345"), ("447911123456", "447911123456"),
    ("", ""), (None, ""),
]


def run():
    failures = 0
    for raw, expected in CASES:
        got = normalise_msisdn(raw)
        ok = got == expected
        failures += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] normalise({raw!r}) -> {got!r}"
              + ("" if ok else f"  (expected {expected!r})"))
    for raw, _ in CASES:
        once = normalise_msisdn(raw)
        if once != normalise_msisdn(once):
            failures += 1
            print(f"[FAIL] idempotency: {raw!r}")
    for canon, disp in [(CANONICAL, "0722123456"), ("254110000111", "0110000111"),
                        ("0202345678", "0202345678")]:
        if display_msisdn(canon) != disp:
            failures += 1
            print(f"[FAIL] display({canon!r})")
    print("\n" + ("ALL PASS" if failures == 0 else f"{failures} FAILURE(S)"))
    return failures


if __name__ == "__main__":
    raise SystemExit(1 if run() else 0)
