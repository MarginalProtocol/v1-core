from ape import reverts


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


def test_transfer_helper_safe_transfer_eth(transfer_helper_lib, alice, sender):
    # send some eth into transfer helper lib to seed
    value = int(1e18)
    sender.transfer(transfer_helper_lib.address, value)
    assert transfer_helper_lib.balance == value

    # transfer to alice from helper lib contract
    balance_alice = alice.balance
    transfer_helper_lib.safeTransferETH(alice.address, value, sender=sender)
    assert alice.balance == balance_alice + value
    assert transfer_helper_lib.balance == 0


def test_transfer_helper_safe_transfer_eth__reverts_when_call_fails(
    transfer_helper_lib, alice, sender
):
    # send some eth into transfer helper lib to seed
    value = int(1e18)
    sender.transfer(transfer_helper_lib.address, value)
    assert transfer_helper_lib.balance == value

    # attempt to transfer more than contract has to alice from helper lib contract
    with reverts("STE"):
        transfer_helper_lib.safeTransferETH(alice.address, value + 1, sender=sender)
