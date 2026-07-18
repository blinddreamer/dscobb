import logging
import os
import httpx
import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

JANICE_API_KEY = os.getenv("JANICE_API_KEY", "")
JANICE_URL = "https://janice.e-351.com/api/rest/v2/appraisal"
JANICE_PARAMS = {
    "market": "2",
    "pricing": "buy",
    "pricingVariant": "immediate",
}

ESI_BASE = "https://esi.evetech.net"

# EVE's type/group/category mappings are effectively static, so cache them
# across requests to avoid hammering ESI on every appraisal.
_type_group_cache: Dict[int, Optional[int]] = {}
_group_info_cache: Dict[int, Optional[Tuple[str, int]]] = {}
_category_name_cache: Dict[int, Optional[str]] = {}


def clear_esi_cache() -> None:
    _type_group_cache.clear()
    _group_info_cache.clear()
    _category_name_cache.clear()


@dataclass
class AppraisalItem:
    name: str
    quantity: int
    buy_price: float
    group_name: str
    category_name: str
    lookup_failed: bool = False


class AppraisalError(Exception):
    pass


async def _esi_type_group(client: httpx.AsyncClient, type_id: int) -> Optional[int]:
    try:
        r = await client.get(f"{ESI_BASE}/v3/universe/types/{type_id}/")
        if r.status_code == 200:
            return r.json().get("group_id", 0)
        logger.warning("ESI type lookup for %s returned status %s", type_id, r.status_code)
        return None
    except Exception:
        logger.exception("ESI type lookup failed for type_id=%s", type_id)
        return None


async def _esi_group_info(client: httpx.AsyncClient, group_id: int) -> Optional[Tuple[str, int]]:
    try:
        r = await client.get(f"{ESI_BASE}/v1/universe/groups/{group_id}/")
        if r.status_code == 200:
            d = r.json()
            return d.get("name", ""), d.get("category_id", 0)
        logger.warning("ESI group lookup for %s returned status %s", group_id, r.status_code)
        return None
    except Exception:
        logger.exception("ESI group lookup failed for group_id=%s", group_id)
        return None


async def _esi_category_name(client: httpx.AsyncClient, category_id: int) -> Optional[str]:
    try:
        r = await client.get(f"{ESI_BASE}/v1/universe/categories/{category_id}/")
        if r.status_code == 200:
            return r.json().get("name", "")
        logger.warning("ESI category lookup for %s returned status %s", category_id, r.status_code)
        return None
    except Exception:
        logger.exception("ESI category lookup failed for category_id=%s", category_id)
        return None


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
        logger.warning("Janice request failed: %s", exc)
        raise AppraisalError(str(exc)) from exc

    try:
        data = response.json()
    except Exception as exc:
        logger.exception("Janice returned invalid JSON")
        raise AppraisalError(f"Invalid JSON from Janice: {exc}") from exc

    raw_items = data.get("items", [])
    type_ids = list({
        raw.get("itemType", {}).get("eid")
        for raw in raw_items
        if raw.get("itemType", {}).get("eid")
    })

    type_to_group: Dict[int, Optional[int]] = {}
    group_map: Dict[int, Optional[Tuple[str, int]]] = {}
    cat_map: Dict[int, Optional[str]] = {}

    if type_ids:
        async with httpx.AsyncClient(timeout=10.0) as esi:
            uncached_type_ids = [tid for tid in type_ids if tid not in _type_group_cache]
            if uncached_type_ids:
                results = await asyncio.gather(*[_esi_type_group(esi, tid) for tid in uncached_type_ids])
                for tid, gid in zip(uncached_type_ids, results):
                    _type_group_cache[tid] = gid
            type_to_group = {tid: _type_group_cache[tid] for tid in type_ids}

            group_ids_needed = {gid for gid in type_to_group.values() if gid}
            uncached_groups = [gid for gid in group_ids_needed if gid not in _group_info_cache]
            if uncached_groups:
                results = await asyncio.gather(*[_esi_group_info(esi, gid) for gid in uncached_groups])
                for gid, info in zip(uncached_groups, results):
                    _group_info_cache[gid] = info
            group_map = {gid: _group_info_cache[gid] for gid in group_ids_needed}

            cat_ids_needed = {info[1] for info in group_map.values() if info and info[1]}
            uncached_cats = [cid for cid in cat_ids_needed if cid not in _category_name_cache]
            if uncached_cats:
                results = await asyncio.gather(*[_esi_category_name(esi, cid) for cid in uncached_cats])
                for cid, name in zip(uncached_cats, results):
                    _category_name_cache[cid] = name
            cat_map = {cid: _category_name_cache[cid] for cid in cat_ids_needed}

    group_name_by_type: Dict[int, str] = {}
    category_name_by_type: Dict[int, str] = {}
    lookup_failed_types = set()

    for tid in type_ids:
        gid = type_to_group.get(tid)
        if gid is None:
            lookup_failed_types.add(tid)
            continue
        if not gid:
            continue

        info = group_map.get(gid)
        if info is None:
            lookup_failed_types.add(tid)
            continue

        gname, cat_id = info
        group_name_by_type[tid] = gname
        if not cat_id:
            continue

        cname = cat_map.get(cat_id)
        if cname is None:
            lookup_failed_types.add(tid)
        else:
            category_name_by_type[tid] = cname

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
            lookup_failed=eid in lookup_failed_types,
        ))
    return items
