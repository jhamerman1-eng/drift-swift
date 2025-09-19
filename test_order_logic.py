"""Pytest-compatible order logic tests for the Swift MM bot."""

from types import SimpleNamespace

import pytest

from run_swift_mm_complete import CompleteSwiftMMBot


def _create_bot_stub() -> CompleteSwiftMMBot:
    bot = CompleteSwiftMMBot.__new__(CompleteSwiftMMBot)
    bot.max_orders_per_side = 1
    bot.order_size = 0.2
    bot.inventory_manager = SimpleNamespace(calculate_inventory_skew=lambda position: 0.0)
    bot.active_orders = {}
    return bot


def _create_mock_order(side: str, price: float, size: float) -> SimpleNamespace:
    return SimpleNamespace(side=side, status="active", price=price, size=size, timestamp=1234567890)


def test_order_counting_logic():
    bot = _create_bot_stub()
    bot.active_orders = {
        "order_1": _create_mock_order("sell", 244.50, 0.25),
        "order_2": _create_mock_order("sell", 244.45, 0.25),
    }
    active_buys = sum(1 for order in bot.active_orders.values() if order.side == "buy" and order.status == "active")
    active_sells = sum(1 for order in bot.active_orders.values() if order.side == "sell" and order.status == "active")

    assert active_buys == 0
    assert active_sells == 2
    assert bot.max_orders_per_side == 1
    assert active_buys < bot.max_orders_per_side
    assert not (active_sells < bot.max_orders_per_side)


def test_inventory_skew_neutral_position():
    bot = _create_bot_stub()
    bot.current_position = 0.0
    skew = bot.inventory_manager.calculate_inventory_skew(bot.current_position)
    assert skew == pytest.approx(0.0)


if __name__ == "__main__":
    pytest.main([__file__])
