import pytest
from app.config import get_config


def test_defaults_when_no_env_vars(monkeypatch):
    monkeypatch.delenv("ALLOWED_CATEGORIES", raising=False)
    monkeypatch.delenv("BUYBACK_PERCENTAGE", raising=False)
    monkeypatch.delenv("FIXED_PRICES", raising=False)
    config = get_config()
    assert config.buyback_percentage == 0.80
    assert config.allowed_categories == []
    assert config.fixed_prices == {}


def test_allowed_categories_parsed(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "Ship,Asteroid")
    config = get_config()
    assert config.allowed_categories == ["Ship", "Asteroid"]


def test_allowed_categories_trims_whitespace(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", " Ship , Asteroid ")
    config = get_config()
    assert config.allowed_categories == ["Ship", "Asteroid"]


def test_buyback_percentage_parsed(monkeypatch):
    monkeypatch.setenv("BUYBACK_PERCENTAGE", "85")
    config = get_config()
    assert config.buyback_percentage == 0.85


def test_empty_allowed_categories_blocks_everything(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "")
    config = get_config()
    assert config.allowed_categories == []


def test_fixed_prices_parsed(monkeypatch):
    monkeypatch.setenv("FIXED_PRICES", "Heavy Water:500,Liquid Ozone:120")
    config = get_config()
    assert config.fixed_prices == {"heavy water": 500.0, "liquid ozone": 120.0}


def test_fixed_prices_trims_whitespace(monkeypatch):
    monkeypatch.setenv("FIXED_PRICES", " Heavy Water : 500 ")
    config = get_config()
    assert config.fixed_prices == {"heavy water": 500.0}


def test_empty_fixed_prices(monkeypatch):
    monkeypatch.setenv("FIXED_PRICES", "")
    config = get_config()
    assert config.fixed_prices == {}
