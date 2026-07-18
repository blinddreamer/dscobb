import pytest

from app.janice import clear_esi_cache


@pytest.fixture(autouse=True)
def _reset_esi_cache():
    clear_esi_cache()
    yield
    clear_esi_cache()
