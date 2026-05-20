"""
discover.py — Org-agnostic subscriber name pattern discovery and classification.
"""
import re
from collections import Counter


DANGEROUS_PATTERNS = [re.compile(r"(\w+\+){3,}"), re.compile(r"\(\w+\)\{")]


def detect_org_tokens(names: list[str]) -> list[str]:
    """Extract leading uppercase tokens that appear in >10% of subscriber names."""
    token_counts: Counter = Counter()
    for name in names:
        m = re.match(r"^([A-Z]{2,8})\b", name.upper())
        if m:
            token_counts[m.group(1)] += 1
    threshold = max(2, len(names) * 0.05)
    return [t for t, c in token_counts.items() if c >= threshold]


def classify_name(raw_name: str, rules: list[tuple[str, str]], universal_rules=None) -> str:
    """Apply user rules then universal fallback rules to classify a subscriber name."""
    name_upper = raw_name.upper()
    for pattern, division in rules:
        if _safe_match(pattern, name_upper):
            return division
    if universal_rules:
        for pattern, division in universal_rules:
            if _safe_match(pattern, name_upper):
                return division
    return "Unclassified"


def _safe_match(pattern: str, text: str) -> bool:
    if len(pattern) > 200:
        return False
    for dangerous in DANGEROUS_PATTERNS:
        if dangerous.search(pattern):
            return False
    try:
        return bool(re.search(pattern, text))
    except re.error:
        return False


def discover_patterns(names: list[str]) -> list[dict]:
    """Return discovered leading code tokens with counts and sample names."""
    token_map: dict[str, list[str]] = {}
    for name in names:
        m = re.match(r"^([A-Z]{2,8})\b", name.strip().upper())
        if m:
            tok = m.group(1)
            token_map.setdefault(tok, []).append(name)
    result = []
    for tok, samples in sorted(token_map.items(), key=lambda x: -len(x[1])):
        result.append({
            "token": tok,
            "count": len(samples),
            "samples": samples[:3],
        })
    return result
