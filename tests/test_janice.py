import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.janice import appraise, AppraisalItem, AppraisalError


SAMPLE_RESPONSE = {
    "items": [
        {
            "itemType": {
                "name": "Glacial Mass",
                "groupName": "Ice",
                "categoryName": "Asteroid",
            },
            "amount": 100,
            "effectivePrices": {"buy": 10000.0},
        },
        {
            "itemType": {
                "name": "Tritanium",
                "groupName": "Mineral",
                "categoryName": "Material",
            },
            "amount": 1000,
            "effectivePrices": {"buy": 5.0},
        },
    ]
}


def make_mock_client(status_code: int, json_body: dict):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.json.return_value = json_body
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=mock_response
        )
    else:
        mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

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
