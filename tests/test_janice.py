import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.janice import appraise, AppraisalItem, AppraisalError


SAMPLE_RESPONSE = {
    "items": [
        {
            "itemType": {"eid": 16262, "name": "Glacial Mass", "volume": 1000.0},
            "amount": 100,
            "effectivePrices": {"buyPrice": 10000.0},
        },
        {
            "itemType": {"eid": 34, "name": "Tritanium", "volume": 0.01},
            "amount": 1000,
            "effectivePrices": {"buyPrice": 5.0},
        },
    ]
}

ESI_TYPES = {
    16262: {"type_id": 16262, "name": "Glacial Mass", "group_id": 465},
    34: {"type_id": 34, "name": "Tritanium", "group_id": 18},
}
ESI_GROUPS = {
    465: {"group_id": 465, "name": "Ice", "category_id": 25},
    18: {"group_id": 18, "name": "Mineral", "category_id": 4},
}
ESI_CATEGORIES = {
    25: {"category_id": 25, "name": "Asteroid"},
    4: {"category_id": 4, "name": "Material"},
}


def _make_esi_response(data):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = data
    return r


def make_mock_client(janice_status: int, janice_body: dict):
    janice_response = MagicMock()
    janice_response.status_code = janice_status
    janice_response.json.return_value = janice_body
    if janice_status >= 400:
        janice_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=janice_response
        )
    else:
        janice_response.raise_for_status = MagicMock()

    async def mock_get(url, **kwargs):
        if "/universe/types/" in url:
            type_id = int(url.split("/universe/types/")[1].rstrip("/"))
            return _make_esi_response(ESI_TYPES.get(type_id, {}))
        elif "/universe/groups/" in url:
            group_id = int(url.split("/universe/groups/")[1].rstrip("/"))
            return _make_esi_response(ESI_GROUPS.get(group_id, {}))
        elif "/universe/categories/" in url:
            cat_id = int(url.split("/universe/categories/")[1].rstrip("/"))
            return _make_esi_response(ESI_CATEGORIES.get(cat_id, {}))
        return _make_esi_response({})

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=janice_response)
    mock_client.get = mock_get

    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=None)
    return mock_cm


async def test_appraise_returns_parsed_items():
    mock_cm = make_mock_client(200, SAMPLE_RESPONSE)
    with patch("app.janice.httpx.AsyncClient", return_value=mock_cm):
        result = await appraise("Glacial Mass\t100\nTritanium\t1000")

    assert len(result) == 2
    assert result[0].name == "Glacial Mass"
    assert result[0].quantity == 100
    assert result[0].buy_price == 10000.0
    assert result[0].group_name == "Ice"
    assert result[0].category_name == "Asteroid"


async def test_appraise_returns_second_item():
    mock_cm = make_mock_client(200, SAMPLE_RESPONSE)
    with patch("app.janice.httpx.AsyncClient", return_value=mock_cm):
        result = await appraise("Glacial Mass\t100\nTritanium\t1000")

    assert result[1].name == "Tritanium"
    assert result[1].buy_price == 5.0
    assert result[1].group_name == "Mineral"


async def test_appraise_raises_on_http_error():
    mock_cm = make_mock_client(503, {})
    with patch("app.janice.httpx.AsyncClient", return_value=mock_cm):
        with pytest.raises(AppraisalError):
            await appraise("Glacial Mass\t100")


async def test_appraise_raises_on_timeout():
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch("app.janice.httpx.AsyncClient", return_value=mock_cm):
        with pytest.raises(AppraisalError):
            await appraise("Glacial Mass\t100")


async def test_appraise_empty_items_list():
    mock_cm = make_mock_client(200, {"items": []})
    with patch("app.janice.httpx.AsyncClient", return_value=mock_cm):
        result = await appraise("SomeUnknownItem\t1")
    assert result == []
