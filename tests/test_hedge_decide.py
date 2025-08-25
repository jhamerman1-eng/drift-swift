from bots.hedge.decide import decide_hedge
def test_decide_hedge_stub():
    hi = decide_hedge(100000)
    lo = decide_hedge(1000)
    assert hi['urgency'] == 'high' and lo['urgency'] == 'normal'
