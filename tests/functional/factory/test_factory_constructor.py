def test_constructor_sets_univ3_factory(factory, mock_univ3_factory):
    assert factory.uniswapV3Factory() == mock_univ3_factory.address


def test_constructor__enables_leverages(factory, mock_univ3_factory):
    assert factory.getLeverage(250000) == 4333333
    assert factory.getLeverage(500000) == 2818181
    assert factory.getLeverage(1000000) == 1952380
