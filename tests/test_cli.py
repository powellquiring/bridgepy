from bridgepy import *
import io
import json

def test_bid():
    hand = bid_parse("w3sm3")
    assert(hand == Result(Team.WE, 3, Suit.SPADE, 0, Honors.NONE, Double.NONE))
    hand = bid_parse("w3sd1")
    assert(hand.over == -1)
    hand = bid_parse("w3nm3d")
    assert(hand == Result(Team.WE, 3, Suit.NOTRUMP, 0, Honors.NONE, Double.DOUBLE))
    hand = bid_parse("w3nm3r")
    assert(hand == Result(Team.WE, 3, Suit.NOTRUMP, 0, Honors.NONE, Double.REDOUBLE))
    hand = bid_parse("w3nm30r")
    assert(hand == Result(Team.WE, 3, Suit.NOTRUMP, 0, Honors.H100, Double.REDOUBLE))
    hand = bid_parse("w3nm3r5")
    assert(hand == Result(Team.WE, 3, Suit.NOTRUMP, 0, Honors.H150, Double.REDOUBLE))

def test_score():
    """ example comes from wikipedia"""
    r = Rubber()
    assert(not r.complete())
    assert(r.total[Team.WE.value] == 0)
    assert(r.total[Team.THEY.value] == 0)
    r.add(bid_parse('w2nm3')) #1
    assert(r.games[0][Team.WE.value][0] == 70)
    assert(r.above[Team.WE.value][0] == 30)
    r.add(bid_parse('t4hm4')) #2
    r.add(bid_parse('t5cd2')) #3
    assert(r.above[Team.WE.value][0] == 30)
    assert(r.above[Team.WE.value][1] == 200)
    assert(r.games[0][Team.THEY.value][0] == 120)
    r.add(bid_parse('w4sm5d')) #4
    assert(r.above[Team.WE.value][2] == 100)
    assert(r.above[Team.WE.value][3] == 50)
    assert(r.games[1][Team.WE.value][0] == 240)
    r.add(bid_parse('w3cm4')) #5
    r.add(bid_parse('t6dm65')) #6
    assert(r.above[Team.WE.value][4] == 20)
    assert(r.above[Team.WE.value][3] == 50)
    assert(r.above[Team.THEY.value][0] == 750)
    assert(r.above[Team.THEY.value][1] == 150)
    assert(r.above[Team.THEY.value][2] == 500)
    assert(r.games[2][Team.WE.value][0] == 60)
    assert(r.games[2][Team.THEY.value][0] == 120)
    assert(r.total[Team.WE.value] == 770)
    assert(r.total[Team.THEY.value] == 1640)


#def test_cli():
#    f = io.StringIO("")
#    bid_file(f, "w3sm3")
#    f.seek(0)
#    result = json.load(f)
#    expected = json.loads('[{"team": "w", "suit": "s", "bid": 3, "made": 3}]')
#    assert(result == expected)
