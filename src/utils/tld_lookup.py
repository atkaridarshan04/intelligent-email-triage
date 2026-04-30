"""
TLD risk score lookup.
Loads data/tld_risk_scores.json and returns a score (1-3) for any TLD.
"""

import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "tld_risk_scores.json"

def _load() -> dict:
    with open(_DATA_PATH) as f:
        return json.load(f)

_TABLE = _load()
_SCORES = _TABLE["scores"]

# Build flat TLD → score map
_TLD_MAP: dict[str, int] = {}
for tier, tlds in _TABLE.items():
    if tier == "scores":
        continue
    for tld in tlds:
        _TLD_MAP[tld] = _SCORES[tier]


def get_tld_score(domain: str) -> int:
    """
    Returns risk score for the TLD of a domain.
    1 = low risk, 2 = medium risk, 3 = high risk.
    Unknown TLDs default to 2 (medium).

    >>> get_tld_score("paypal.com")
    1
    >>> get_tld_score("malicious.xyz")
    3
    >>> get_tld_score("something.info")
    2
    """
    if not domain:
        return _SCORES["unknown"]
    tld = "." + domain.rstrip(".").rsplit(".", 1)[-1].lower()
    return _TLD_MAP.get(tld, _SCORES["unknown"])


if __name__ == "__main__":
    import doctest
    doctest.testmod(verbose=True)
