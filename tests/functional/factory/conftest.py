import pytest


@pytest.fixture(scope="module")
def factory(project, accounts):
    return project.MarginalV1Factory.deploy(sender=accounts[0])
