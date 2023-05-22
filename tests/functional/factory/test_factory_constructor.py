def test_constructor_sets_univ3_factory(factory, mock_univ3_factory):
    assert factory.uniswapV3Factory() == mock_univ3_factory.address


def test_constructor__enables_leverages(factory, mock_univ3_factory):
    assert factory.getLeverage(250000) == 5000000
    assert factory.getLeverage(500000) == 3000000
    assert factory.getLeverage(1000000) == 2000000
