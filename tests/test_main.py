import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.janice import AppraisalItem, AppraisalError


def make_item(name: str, quantity: int, buy_price: float, group_name: str) -> AppraisalItem:
    return AppraisalItem(
        name=name,
        quantity=quantity,
        buy_price=buy_price,
        group_name=group_name,
        category_name="Asteroid",
    )


def get_client():
    from app.main import app
    return TestClient(app)


def test_get_root_renders_form():
    client = get_client()
    response = client.get("/")
    assert response.status_code == 200
    assert "<textarea" in response.text
    assert 'action="/appraise"' in response.text


def test_post_empty_paste_shows_error():
    client = get_client()
    response = client.post("/appraise", data={"items": "   "})
    assert response.status_code == 200
    assert "Please paste some items" in response.text


def test_post_appraise_shows_item_breakdown(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "Ice")
    monkeypatch.setenv("BUYBACK_PERCENTAGE", "90")
    items = [make_item("Glacial Mass", 100, 10000.0, "Ice")]

    client = get_client()
    with patch("app.main.appraise", new=AsyncMock(return_value=items)):
        response = client.post("/appraise", data={"items": "Glacial Mass\t100"})

    assert response.status_code == 200
    assert "Glacial Mass" in response.text
    assert "9,000.00" in response.text
    assert "900,000.00" in response.text


def test_post_appraise_grand_total(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "Ice")
    monkeypatch.setenv("BUYBACK_PERCENTAGE", "90")
    items = [
        make_item("Glacial Mass", 10, 10000.0, "Ice"),
        make_item("White Glaze", 20, 5000.0, "Ice"),
    ]

    client = get_client()
    with patch("app.main.appraise", new=AsyncMock(return_value=items)):
        response = client.post("/appraise", data={"items": "Glacial Mass\t10\nWhite Glaze\t20"})

    assert response.status_code == 200
    assert "180,000.00" in response.text


def test_post_appraise_rejects_unlisted_category(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "Ice")
    items = [make_item("Tritanium", 1000, 5.0, "Mineral")]

    client = get_client()
    with patch("app.main.appraise", new=AsyncMock(return_value=items)):
        response = client.post("/appraise", data={"items": "Tritanium\t1000"})

    assert response.status_code == 200
    assert "category not accepted" in response.text
    assert "Tritanium" in response.text


def test_post_appraise_accepts_listed_category(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "Ice")
    items = [make_item("Glacial Mass", 100, 10000.0, "Ice")]

    client = get_client()
    with patch("app.main.appraise", new=AsyncMock(return_value=items)):
        response = client.post("/appraise", data={"items": "Glacial Mass\t100"})

    assert response.status_code == 200
    assert "Glacial Mass" in response.text
    assert "category not accepted" not in response.text


def test_post_appraise_shows_error_on_api_failure():
    client = get_client()
    with patch("app.main.appraise", new=AsyncMock(side_effect=AppraisalError("timeout"))):
        response = client.post("/appraise", data={"items": "Glacial Mass\t100"})

    assert response.status_code == 200
    assert "Price service unavailable" in response.text


def test_post_appraise_rejects_not_found_item(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "Ice")
    items = [make_item("GarbageItem", 1, 0.0, "Ice")]

    client = get_client()
    with patch("app.main.appraise", new=AsyncMock(return_value=items)):
        response = client.post("/appraise", data={"items": "GarbageItem\t1"})

    assert response.status_code == 200
    assert "not found" in response.text


def test_post_appraise_accepts_item_matching_category_name(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "Asteroid")
    item = AppraisalItem(name="Glacial Mass", quantity=10, buy_price=10000.0, group_name="Ice", category_name="Asteroid")

    client = get_client()
    with patch("app.main.appraise", new=AsyncMock(return_value=[item])):
        response = client.post("/appraise", data={"items": "Glacial Mass\t10"})

    assert response.status_code == 200
    assert "Glacial Mass" in response.text
    assert "category not accepted" not in response.text


def test_post_appraise_empty_allowed_blocks_everything(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "")
    items = [make_item("Tritanium", 1000, 5.0, "Mineral")]

    client = get_client()
    with patch("app.main.appraise", new=AsyncMock(return_value=items)):
        response = client.post("/appraise", data={"items": "Tritanium\t1000"})

    assert response.status_code == 200
    assert "category not accepted" in response.text


def test_post_appraise_all_rejected_grand_total_zero(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "Ice")
    items = [make_item("Tritanium", 1000, 5.0, "Mineral")]

    client = get_client()
    with patch("app.main.appraise", new=AsyncMock(return_value=items)):
        response = client.post("/appraise", data={"items": "Tritanium\t1000"})

    assert response.status_code == 200
    assert "0.00" in response.text
