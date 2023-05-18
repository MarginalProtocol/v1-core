def test_constructor__enables_leverages(factory):
    assert factory.getLeverage(250000) == 5000000
    assert factory.getLeverage(500000) == 3000000
    assert factory.getLeverage(1000000) == 2000000
