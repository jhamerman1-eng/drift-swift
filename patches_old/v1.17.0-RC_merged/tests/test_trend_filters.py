from bots.trend.filters import pass_filters
def test_trend_filters_stub():
    assert pass_filters(atr=1.0, adx=20)
    assert not pass_filters(atr=0.5, adx=10)
