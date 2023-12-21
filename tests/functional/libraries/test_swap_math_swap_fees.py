import pytest

from hypothesis import given
from hypothesis import strategies as st

from utils.constants import FEE, FEE_UNIT


def test_swap_math_swap_fees__with_amount_in(swap_math_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    amount_in = x * 1 // 100  # 1% of reserves in
    fees = (amount_in * FEE) // FEE_UNIT
    assert swap_math_lib.swapFees(amount_in, FEE, False) == fees


def test_swap_math_swap_fees__with_amount_in_less_fee(swap_math_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    amount_in = x * 1 // 100  # 1% of reserves in
    amount_in_less_fee = amount_in - (amount_in * FEE) // FEE_UNIT
    fees = (amount_in_less_fee * FEE) // (FEE_UNIT - FEE)

    assert swap_math_lib.swapFees(amount_in_less_fee, FEE, True) == fees
    assert fees == (amount_in - amount_in_less_fee)


@pytest.mark.fuzzing
@pytest.mark.parametrize("less_fee", [True, False])
@given(amount=st.integers(min_value=0, max_value=2**256 - 1))
def test_swap_math_swap_fees__with_fuzz(swap_math_lib, amount, less_fee):
    # ignore the overflow swap case
    if amount * FEE > 2**256 - 1:
        return

    fees = (
        (amount * FEE) // FEE_UNIT
        if not less_fee
        else (amount * FEE) // (FEE_UNIT - FEE)
    )
    assert swap_math_lib.swapFees(amount, FEE, less_fee) == fees
