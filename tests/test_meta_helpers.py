import json
from kidscompass.data import handover_day_counts


def test_handover_day_policy_neutral():
    meta = {'anchor_year':2025,'assigned':'special','handovers':[{'date':'2024-12-25','time':'18:00','role':'end'}]}
    mj = json.dumps(meta)
    assert handover_day_counts(mj) is False


def test_no_handovers_counts_true():
    meta = {'anchor_year':2025,'assigned':'first'}
    mj = json.dumps(meta)
    assert handover_day_counts(mj) is True
