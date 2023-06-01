def test_transfer_helper_safe_transfer__with_value_less_than_balance(
    transfer_helper_lib, token_a, alice
):
    balance = int(1e6 * 10 ** (token_a.decimals()))
    token_a.mint(transfer_helper_lib.address, balance, sender=alice)

    value = balance - 1
    transfer_helper_lib.safeTransfer(
        token_a.address, alice.address, value, sender=alice
    )
    assert token_a.balanceOf(alice.address) == value
    assert token_a.balanceOf(transfer_helper_lib.address) == 1


def test_transfer_helper_safe_transfer__with_value_greater_than_balance(
    transfer_helper_lib, token_a, alice
):
    balance = int(1e6 * 10 ** (token_a.decimals()))
    token_a.mint(transfer_helper_lib.address, balance, sender=alice)

    value = balance + 1
    transfer_helper_lib.safeTransfer(
        token_a.address, alice.address, value, sender=alice
    )
    assert token_a.balanceOf(alice.address) == balance
    assert token_a.balanceOf(transfer_helper_lib.address) == 0
