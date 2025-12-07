import pytest

from mcod.special_signs.factories import SpecialSignFactory


@pytest.fixture
def special_sign():
    return SpecialSignFactory.create()


@pytest.fixture
def special_signs():
    return SpecialSignFactory.create_batch(2)
