import pytest

from hypothesis import given
from hypothesis import strategies as st

from utils.constants import REWARD_UNIT, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM


def test_position_liquidation_rewards__with_base_fee_greater_than_min(position_lib):
    base_fee = BASE_FEE_MIN * 2
    rewards = (base_fee * GAS_LIQUIDATE * REWARD_PREMIUM) // REWARD_UNIT
    result = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )
    assert result == rewards


def test_position_liquidation_rewards__with_base_fee_less_than_min(position_lib):
    base_fee = BASE_FEE_MIN // 2
    rewards = (BASE_FEE_MIN * GAS_LIQUIDATE * REWARD_PREMIUM) // REWARD_UNIT
    result = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )
    assert result == rewards


@pytest.mark.fuzzing
@given(
    base_fee=st.integers(min_value=0, max_value=2**200 - 1),
)
def test_position_liquidation_rewards__with_fuzz(position_lib, base_fee):
    base = base_fee if base_fee > BASE_FEE_MIN else BASE_FEE_MIN
    rewards = (base * GAS_LIQUIDATE * REWARD_PREMIUM) // REWARD_UNIT
    result = position_lib.liquidationRewards(
        base_fee, BASE_FEE_MIN, GAS_LIQUIDATE, REWARD_PREMIUM
    )
    assert result == rewards
