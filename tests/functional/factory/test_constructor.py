import pytest


@pytest.fixture
def factory(project, deployer):
    return project.MarginalV1Factory.deploy(sender=deployer)


def test_constructor_enables_leverages(factory):
    assert factory.getLeverage(2500) == 50000
    assert factory.getLeverage(5000) == 30000
    assert factory.getLeverage(10000) == 20000
