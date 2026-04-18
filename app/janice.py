import httpx
from dataclasses import dataclass
from typing import List

# Public free sample key from Janice docs.
# See https://janice.e-351.com/api/rest/docs for details.
JANICE_API_KEY = "G9KwKq3465588VPd6747t95Zh94q3W2E"
JANICE_URL = "https://janice.e-351.com/api/rest/v2/appraisal"
JANICE_PARAMS = {
    "market": "2",
    "designation": "name",
    "pricing": "buy",
    "pricingVariant": "immediate",
}


@dataclass
class AppraisalItem:
    name: str
    quantity: int
    buy_price: float
    group_name: str
    category_name: str


class AppraisalError(Exception):
    pass


async def appraise(paste: str) -> List[AppraisalItem]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                JANICE_URL,
                params=JANICE_PARAMS,
                headers={
                    "X-ApiKey": JANICE_API_KEY,
                    "Content-Type": "text/plain",
                },
                content=paste.encode(),
            )
            response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        raise AppraisalError(str(exc)) from exc

    try:
        data = response.json()
    except Exception as exc:
        raise AppraisalError(f"Invalid JSON from Janice: {exc}") from exc

    items = []
    for raw in data.get("items", []):
        item_type = raw.get("itemType", {})
        prices = raw.get("effectivePrices", {})
        items.append(
            AppraisalItem(
                name=item_type.get("name", "Unknown"),
                quantity=raw.get("amount", 0),
                buy_price=prices.get("buy", 0.0),
                group_name=item_type.get("groupName", ""),
                category_name=item_type.get("categoryName", ""),
            )
        )
    return items
