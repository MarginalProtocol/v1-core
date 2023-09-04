import pytest

from hypothesis import given
from hypothesis import strategies as st

from utils.constants import FEE, FEE_UNIT


def test_swap_math_swap_fees(swap_math_lib):
    x = int(125.04e12)  # e.g. USDC reserves
    amount_in = x * 1 // 100  # 1% of reserves in
    fees = (amount_in * FEE) // FEE_UNIT
    assert swap_math_lib.swapFees(amount_in, FEE) == fees


@pytest.mark.fuzzing
@given(amount_in=st.integers(min_value=0, max_value=2**256 - 1))
def test_swap_math_swap_fees__with_fuzz(swap_math_lib, amount_in):
    # ignore the overflow swap case
    if amount_in * FEE > 2**256 - 1:
        return

    fees = (amount_in * FEE) // FEE_UNIT
    assert swap_math_lib.swapFees(amount_in, FEE) == fees
