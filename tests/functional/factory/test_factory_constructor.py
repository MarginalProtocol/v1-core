import pytest


@pytest.fixture
def rando_univ3_observation_cardinality():
    return 300  # fits 1h TWAP at 1 obs per block for 12s blocks


def test_constructor_sets_univ3_factory(
    factory, mock_univ3_factory, rando_univ3_observation_cardinality
):
    assert factory.uniswapV3Factory() == mock_univ3_factory.address
    assert (
        factory.observationCardinalityMinimum() == rando_univ3_observation_cardinality
    )


def test_constructor__enables_leverages(factory, mock_univ3_factory):
    assert factory.getLeverage(250000) == 4333333
    assert factory.getLeverage(500000) == 2818181
    assert factory.getLeverage(1000000) == 1952380
