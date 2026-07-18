import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Config:
    buyback_percentage: float
    allowed_categories: List[str]
    fixed_prices: Dict[str, float]
    fixed_price_display: List[Tuple[str, float]]


def get_config() -> Config:
    raw_pct = os.getenv("BUYBACK_PERCENTAGE", "80")
    try:
        pct = float(raw_pct) / 100.0
    except ValueError:
        logger.warning("Invalid BUYBACK_PERCENTAGE=%r, falling back to 80", raw_pct)
        pct = 0.80

    cats_str = os.getenv("ALLOWED_CATEGORIES", "")
    cats = [c.strip() for c in cats_str.split(",") if c.strip()]

    fixed_str = os.getenv("FIXED_PRICES", "")
    fixed_prices: Dict[str, float] = {}
    fixed_price_display: List[Tuple[str, float]] = []
    for entry in fixed_str.split(","):
        entry = entry.strip()
        if not entry:
            continue
        name, _, price = entry.rpartition(":")
        if not name:
            continue
        name = name.strip()
        try:
            price_value = float(price.strip())
        except ValueError:
            logger.warning("Invalid FIXED_PRICES entry %r, skipping", entry)
            continue
        fixed_prices[name.lower()] = price_value
        fixed_price_display.append((name, price_value))

    return Config(
        buyback_percentage=pct,
        allowed_categories=cats,
        fixed_prices=fixed_prices,
        fixed_price_display=fixed_price_display,
    )
