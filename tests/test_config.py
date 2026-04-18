import pytest
from app.config import get_config


def test_defaults_when_no_env_vars(monkeypatch):
    monkeypatch.delenv("ALLOWED_CATEGORIES", raising=False)
    monkeypatch.delenv("BUYBACK_PERCENTAGE", raising=False)
    config = get_config()
    assert config.buyback_percentage == 0.90
    assert config.allowed_categories == []


def test_allowed_categories_parsed(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "Ice,Ore")
    config = get_config()
    assert config.allowed_categories == ["Ice", "Ore"]


def test_allowed_categories_trims_whitespace(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", " Ice , Ore ")
    config = get_config()
    assert config.allowed_categories == ["Ice", "Ore"]


def test_buyback_percentage_parsed(monkeypatch):
    monkeypatch.setenv("BUYBACK_PERCENTAGE", "85")
    config = get_config()
    assert config.buyback_percentage == 0.85


def test_empty_allowed_categories_means_all_accepted(monkeypatch):
    monkeypatch.setenv("ALLOWED_CATEGORIES", "")
    config = get_config()
    assert config.allowed_categories == []
