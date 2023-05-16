import pytest


@pytest.fixture(scope="module")
def sqrt_price_math_lib(project, deployer):
    return project.MockSqrtPriceMath.deploy(sender=deployer)
