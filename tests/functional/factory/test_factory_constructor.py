def test_constructor__enables_leverages(factory):
    assert factory.getLeverage(2500) == 50000
    assert factory.getLeverage(5000) == 30000
    assert factory.getLeverage(10000) == 20000
