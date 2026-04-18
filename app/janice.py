import httpx
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Tuple

JANICE_API_KEY = "G9KwKq3465588VPd6747t95Zh94q3W2E"
JANICE_URL = "https://janice.e-351.com/api/rest/v2/appraisal"
JANICE_PARAMS = {
    "market": "2",
    "pricing": "buy",
    "pricingVariant": "immediate",
}

ESI_BASE = "https://esi.evetech.net"


@dataclass
class AppraisalItem:
    name: str
    quantity: int
    buy_price: float
    group_name: str
    category_name: str


class AppraisalError(Exception):
    pass


async def _esi_type_group(client: httpx.AsyncClient, type_id: int) -> int:
    try:
        r = await client.get(f"{ESI_BASE}/v3/universe/types/{type_id}/")
        return r.json().get("group_id", 0) if r.status_code == 200 else 0
    except Exception:
        return 0


async def _esi_group_info(client: httpx.AsyncClient, group_id: int) -> Tuple[str, int]:
    try:
        r = await client.get(f"{ESI_BASE}/v1/universe/groups/{group_id}/")
        if r.status_code == 200:
            d = r.json()
            return d.get("name", ""), d.get("category_id", 0)
    except Exception:
        pass
    return "", 0


async def _esi_category_name(client: httpx.AsyncClient, category_id: int) -> str:
    try:
        r = await client.get(f"{ESI_BASE}/v1/universe/categories/{category_id}/")
        return r.json().get("name", "") if r.status_code == 200 else ""
    except Exception:
        return ""


async def appraise(paste: str) -> List[AppraisalItem]:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                JANICE_URL,
                params=JANICE_PARAMS,
                headers={"X-ApiKey": JANICE_API_KEY, "Content-Type": "text/plain"},
                content=paste.encode(),
            )
            response.raise_for_status()
    except (httpx.RequestError, httpx.HTTPStatusError) as exc:
        raise AppraisalError(str(exc)) from exc

    try:
        data = response.json()
    except Exception as exc:
        raise AppraisalError(f"Invalid JSON from Janice: {exc}") from exc

    raw_items = data.get("items", [])
    type_ids = list({
        raw.get("itemType", {}).get("eid")
        for raw in raw_items
        if raw.get("itemType", {}).get("eid")
    })

    group_name_by_type: Dict[int, str] = {}
    category_name_by_type: Dict[int, str] = {}

    if type_ids:
        async with httpx.AsyncClient(timeout=10.0) as esi:
            group_ids = await asyncio.gather(*[_esi_type_group(esi, tid) for tid in type_ids])
            type_to_group = dict(zip(type_ids, group_ids))

            unique_groups = list({gid for gid in group_ids if gid})
            group_infos = await asyncio.gather(*[_esi_group_info(esi, gid) for gid in unique_groups])
            group_map = dict(zip(unique_groups, group_infos))

            unique_cats = list({cat_id for _, cat_id in group_infos if cat_id})
            cat_names = await asyncio.gather(*[_esi_category_name(esi, cid) for cid in unique_cats])
            cat_map = dict(zip(unique_cats, cat_names))

        for tid in type_ids:
            gid = type_to_group.get(tid, 0)
            gname, cat_id = group_map.get(gid, ("", 0))
            group_name_by_type[tid] = gname
            category_name_by_type[tid] = cat_map.get(cat_id, "")

    items = []
    for raw in raw_items:
        item_type = raw.get("itemType", {})
        prices = raw.get("effectivePrices", {})
        eid = item_type.get("eid", 0)
        items.append(AppraisalItem(
            name=item_type.get("name", "Unknown"),
            quantity=raw.get("amount", 0),
            buy_price=prices.get("buyPrice", 0.0),
            group_name=group_name_by_type.get(eid, ""),
            category_name=category_name_by_type.get(eid, ""),
        ))
    return items
