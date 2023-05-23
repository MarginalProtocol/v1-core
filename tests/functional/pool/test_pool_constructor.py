def test_pool_constructor__sets_params(factory, pool, mock_univ3_pool):
    assert pool.factory() == factory.address
    assert pool.oracle() == mock_univ3_pool.address
    assert pool.token0() == mock_univ3_pool.token0()
    assert pool.token1() == mock_univ3_pool.token1()
    assert pool.fee() == 1000
    assert pool.maintenance() == 250000