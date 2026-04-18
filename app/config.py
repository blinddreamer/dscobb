import os
from dataclasses import dataclass
from typing import List


@dataclass
class Config:
    buyback_percentage: float
    allowed_categories: List[str]


def get_config() -> Config:
    pct = float(os.getenv("BUYBACK_PERCENTAGE", "90")) / 100.0

    cats_str = os.getenv("ALLOWED_CATEGORIES", "")
    cats = [c.strip() for c in cats_str.split(",") if c.strip()]

    return Config(buyback_percentage=pct, allowed_categories=cats)
