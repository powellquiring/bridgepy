# See README for setup.  It is required to get some environment variables in place to run thee tests
from bridgepy import *
import io
import json
from click.testing import CliRunner
import os
import time

FAST = False


def bucket_name_str() -> str:
    return time.strftime("pfqtest-%Y-%m-%d-%H-%M-%S")


def storage_test(result_storage):
    assert result_storage != None
    # first time, there are no existing results
    hands = result_storage.existing_results()
    assert hands == []
    hands.append(bid_parse("w1sm1"))
    result_storage.store_results(hands)
    stored_hands = result_storage.existing_results()
    assert hands == stored_hands
    hands.append(bid_parse("w3nm3"))
    result_storage.store_results(hands)
    stored_hands = result_storage.existing_results()
    assert hands == stored_hands
    # start over with a new game
    time.sleep(1)
    hands = result_storage.new_results()
    assert hands == []
    hands.append(bid_parse("w1sm1"))
    result_storage.store_results(hands)
    stored_hands = result_storage.existing_results()
    assert hands == stored_hands


def test_results_file():
    with tempfile.TemporaryDirectory() as dir:
        result_storage = ResultsFile(dir)
        storage_test(result_storage)


params = None


def get_params():
    global params
    if params == None:
        runner = CliRunner()
        result = runner.invoke(
            click_cli, ["--print-params"], auto_envvar_prefix="BRIDGEPY"
        )
        assert result.exit_code == 0
        params = json.loads(result.output)
        assert params["print_params"] == True
        assert params["new_game"] == False
        assert params["simulate_function"] == False
        assert params["storage"] == "cos"
        assert len(params["root_test"]) > 1
        assert len(params["api_key"]) > 8
        assert len(params["cos_instance_id"]) > 8
        assert len(params["cos_service_endpoint"]) > 8
        assert params["bid"] == None
    return params


def get_ResultCOS(params):
    return ResultsCOS(
        params["root_test"],
        params["api_key"],
        params["cos_instance_id"],
        params["cos_service_endpoint"],
    )


def test_results_COS():
    if FAST:
        return
    params = get_params()
    result_storage = get_ResultCOS(params)
    storage_test(result_storage)


def test_bid():
    hand = bid_parse("w3sm3")
    assert hand == Result(Team.WE, 3, Suit.SPADE, 0, Honors.NONE, Double.NONE)
    hand = bid_parse("w3sd1")
    assert hand.over == -1
    hand = bid_parse("w3nm3d")
    assert hand == Result(Team.WE, 3, Suit.NOTRUMP, 0, Honors.NONE, Double.DOUBLE)
    hand = bid_parse("w3nm3r")
    assert hand == Result(Team.WE, 3, Suit.NOTRUMP, 0, Honors.NONE, Double.REDOUBLE)
    hand = bid_parse("w3nm30r")
    assert hand == Result(Team.WE, 3, Suit.NOTRUMP, 0, Honors.H100, Double.REDOUBLE)
    hand = bid_parse("w3nm3r5")
    assert hand == Result(Team.WE, 3, Suit.NOTRUMP, 0, Honors.H150, Double.REDOUBLE)


def test_score():
    """ example comes from wikipedia"""
    r = Rubber()
    assert not r.complete()
    assert r.total[Team.WE.value] == 0
    assert r.total[Team.THEY.value] == 0
    r.add(bid_parse("w2nm3"))  # 1
    assert r.games[0][Team.WE.value][0] == 70
    assert r.above[Team.WE.value][0] == 30
    r.add(bid_parse("t4hm4"))  # 2
    r.add(bid_parse("t5cd2"))  # 3
    assert r.above[Team.WE.value][0] == 30
    assert r.above[Team.WE.value][1] == 200
    assert r.games[0][Team.THEY.value][0] == 120
    r.add(bid_parse("w4sm5d"))  # 4
    assert r.above[Team.WE.value][2] == 100
    assert r.above[Team.WE.value][3] == 50
    assert r.games[1][Team.WE.value][0] == 240
    r.add(bid_parse("w3cm4"))  # 5
    r.add(bid_parse("t6dm65"))  # 6
    assert r.above[Team.WE.value][4] == 20
    assert r.above[Team.WE.value][3] == 50
    assert r.above[Team.THEY.value][0] == 750
    assert r.above[Team.THEY.value][1] == 150
    assert r.above[Team.THEY.value][2] == 500
    assert r.games[2][Team.WE.value][0] == 60
    assert r.games[2][Team.THEY.value][0] == 120
    assert r.total[Team.WE.value] == 770
    assert r.total[Team.THEY.value] == 1640


def test_io():
    f = io.StringIO("")
    hands_to_json_file(f, [bid_parse("w3sm3"), bid_parse("w1nd1")])
    f.seek(0)
    hands = hands_from_json_file(f)
    assert len(hands) == 2
    assert hands[0] == Result(Team.WE, 3, Suit.SPADE, 0, Honors.NONE, Double.NONE)
    assert hands[1] == Result(Team.WE, 1, Suit.NOTRUMP, -1, Honors.NONE, Double.NONE)


from pathlib import Path
import tempfile
import time


def test_file():
    with tempfile.TemporaryDirectory() as dir:
        found = True
        try:
            p = existing_game_file(dir)
        except FileNotFoundError:
            found = False
        assert not found
        p = new_game_file(dir)
        p2 = existing_game_file(dir)
        assert p == p2
        time.sleep(1)
        p3 = new_game_file(dir)
        assert p != p3
        assert p3 == existing_game_file(dir)

