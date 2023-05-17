import pytest


@pytest.fixture(scope="module")
def sqrt_price_math_lib(project, accounts):
    yield project.MockSqrtPriceMath.deploy(sender=accounts[0])
