"""Production mixing entry points; never write to Live."""
from __future__ import annotations

import json
from urllib.request import urlopen

CHAIN_ROLES = ("vocals", "drums", "bass", "synths", "bus", "plate", "delay", "master")


def fetch_chain(role: str, *, timeout: float = 5.0, opener=urlopen) -> dict:
    """Read local SecondRoom chain data, not a Live application receipt."""
    if role not in CHAIN_ROLES:
        raise ValueError("unknown chain role")
    with opener("http://127.0.0.1:8099/api/chains/" + role, timeout=timeout) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise ValueError("invalid chain response")
    return result
