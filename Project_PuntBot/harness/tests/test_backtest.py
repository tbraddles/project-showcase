from puntbot.backtest import back_profit, break_even_probability, kelly_fraction


def test_break_even_probability_with_commission():
    # At even money (2.0) with 6% commission, you need more than 50% to break even.
    be = break_even_probability(2.0, commission=0.06)
    assert 0.51 < be < 0.53


def test_winning_back_is_net_of_commission():
    profit = back_profit(True, 3.0, stake=1.0, commission=0.06)
    assert abs(profit - 1.88) < 1e-9


def test_losing_back_loses_the_stake():
    assert back_profit(False, 3.0, stake=1.0) == -1.0


def test_kelly_is_zero_when_no_edge():
    assert kelly_fraction(0.40, 2.0, commission=0.06) == 0.0
    assert kelly_fraction(0.60, 2.0, commission=0.06) > 0
