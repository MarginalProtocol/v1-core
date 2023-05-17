import pytest


@pytest.fixture(scope="module")
def sqrt_price_math_lib(project, accounts):
    return project.MockSqrtPriceMath.deploy(sender=accounts[0])


@pytest.fixture(scope="module")
def position_lib(project, accounts):
    return project.MockPosition.deploy(sender=accounts[0])
