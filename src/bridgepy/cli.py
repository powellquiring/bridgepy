import click
import collections
import json
import fastapi
import enum
import io

class Team(enum.Enum):
    WE = 0
    THEY = 1
class Suit(enum.Enum):
    NOTRUMP = 'n'
    SPADE = "s"
    HEART = "h"
    DIAMOND = "d"
    CLUB = "c"
class Honors(enum.IntEnum):
    H100 = 100
    H150 = 150
    NONE = 0
class Double(enum.Enum):
    NONE = 1
    DOUBLE = 2
    REDOUBLE = 4
Result = collections.namedtuple("Result", ["team", "bid", "suit", "over", "honors", "double"], defaults=(Honors.NONE, Double.NONE))

app = fastapi.FastAPI()
hands = []

@app.post("/hand")
async def new_hand():
    global hands
    hands.append({len(hands):"hands"})
    return hands

@app.get("/hands")
async def get_hands():
    global hands
    return hands

@app.get("/hand/{id}")
async def get_hands(id: int):
    global hands
    return hands[id]

def honors_double(s):
    if s == 'd':
        return {"double": Double.DOUBLE}
    elif s == 'r':
        return {"double": Double.REDOUBLE}
    elif s == '0':
        return {"honors": Honors.H100}
    elif s == '5':
        return {"honors": Honors.H150}
    else:
        raise Exception('Honors or double must be d, r, 0, 5 but was', s)

def bid_parse(bid: str) -> Result:
    """
    bid: (wt)N(shdc)(md)M[dr][15], like w3sm2 or w3sd1 both me team WE bid 3 SPADES made 8 tricks, down 1
    0 (wt) - We or They, must choose one
    1 (shdc) - suit
    2 N - bid number in excess of 6
    3 (md) - one of either Made or Down
    4 M - amoutn made or down
    5/6 [dr] - optional double or redouble
    5/6 [05] - optional 100 or 150 honors points
    Examples:
    w3sm25: WE, 3, SPADES, -1, honors 150
    w3sd1d0: WE, 3, SPADES, -1, honors 100, doubled
    w3sm3r: WE, 3, SPADES, 0, Redoubled
    """
    team = Team.WE if bid[0] == 'w' else Team.THEY
    bid_tricks = int(bid[1])
    suit = Suit(bid[2])
    made_or_down = bid[3]
    over_tricks = int(bid[4])
    over_tricks = -over_tricks if made_or_down == "d" else over_tricks - bid_tricks
    ret = Result(team, bid_tricks, suit, over_tricks)
    for indx in range(5, len(bid)):
        ret = ret._replace(**honors_double(bid[indx]))
    return ret

def score_print(hands):
    games = score_hands(hands)
    for game in games:
        (we_above, they_above, we_below, they_below) = game

class Rubber:
    """
    state of a rubber.  Call the add() function to add another hand result to the rubber
    Example
    we | they
    50 | 
    30 | 
    ---------
    70 |
    30 |
    - - - - - 
       | 90
    - - - - - 
    180|90

    above: [[30, 50], []] # above line, over tricks, honors, rubber bonus, ... arranged by time, print in reverse order
    games: [ 
                [[70, 30],[]], # game 1
                [[], [90]] # game 2
            ]
    totoal: [100, 90] # just a sum of everything
    """
    def __init__(self):
        self.above = [[], []] # we and they list above the line
        self.games = [[[], []]] # games below the line, list of games, each game has a list of contracts won for We and They
        self.games_won = [0, 0] # we, they games won
        self.total = [0, 0] # we and they totals
    def complete(self):
        return self.games_won[Team.WE.value] == 2 or self.games_won[Team.THEY.value] == 2
    def add(self, result: Result) -> bool:
        """add the result to the rubber return True if the rubber is now complete"""
        if self.complete():
            raise Exception("Can not add to this Rubber, is is complete")
        contract_winner = result.team.value
        contract_loser = 1 - contract_winner
        vulnerable = self.games_won[contract_winner] == 1
        if result.over >= 0: # made contract
            above_points = [] # apoints earned above the line for this hand
            last_game = self.games[len(self.games) - 1]
            trick_value = 20 if result.suit == Suit.DIAMOND or result.suit == Suit.CLUB else 30
            under_points = trick_value * result.bid * result.double.value
            under_points += 10 if result.suit == Suit.NOTRUMP else 0
            last_game[contract_winner].append(under_points)
            if result.over > 0:
                over_trick_points = 0
                if result.double == Double.NONE:
                    over_trick_points = trick_value * result.over * result.double.value
                else:
                    over_trick_points = 50 * result.over * result.double.value * (2 if vulnerable else 1)
                above_points.append(over_trick_points)
            slam_bonus = 0
            if result.bid == 6:
                slam_bonus = 750 if vulnerable else 500
            if result.bid == 7:
                slam_bonus = 1000 if vulnerable else 1500
            if slam_bonus:
                above_points.append(slam_bonus)
            if result.double != Double.NONE:
                above_points.append(50 if result.double == Double.DOUBLE else 100) # insult
            if result.honors != Honors.NONE:
                above_points.append(result.honors.value)
            if sum(last_game[contract_winner]) >= 100:
                self.games_won[contract_winner] += 1 # keep track of games won for each team
                if self.complete():
                    rubber_bonus = 700 if self.games_won[contract_loser] == 0 else 500
                    above_points.append(rubber_bonus)
                else:
                    self.games.append([[],[]]) # add a new game

            self.above[contract_winner].extend(above_points)
            self.total[contract_winner] += under_points
            self.total[contract_winner] += sum(above_points)
        else: # set
            #          vu   vd      vr   nu  nd      nr
            trick1 =  [100, 200, 0, 400, 50, 100, 0, 200] # vulnerable undoubled, doubled, redoubled, not vulnerable, ...
            trick23 = [100, 300, 0, 600, 50, 200, 0, 400] # vulnerable undoubled, doubled, redoubled, not vulnerable, ...
            trick4 =  [100, 300, 0, 600, 50, 300, 0, 600] # vulnerable undoubled, doubled, redoubled, not vulnerable, ...
            set_tricks = -result.over
            point_index = 4 * (0 if vulnerable else 1) + result.double.value - 1 # double value is 1, 2, 4
            set_points = trick1[point_index] # first set trick
            set_tricks -= 1
            for i in range(0, set_tricks if set_tricks <= 2 else 2):
                set_points += trick23[point_index]
                set_tricks -= 1
            for i in range(0, set_tricks):
                set_points += trick4[point_index]
            self.above[contract_loser].append(set_points)
            self.total[contract_loser] += set_points
        return self.complete()

def Rubbers(results: []) -> []:
    rubber = Rubber()
    ret = [rubber]
    for result in results:
        if not rubber.add(result):
            rubber = Rubber
            ret.append(rubber)
    return ret
def help_print():
    click.echo(cli.get_help(click.Context(cli)))

def hands_read(f: io.FileIO):
    if not f.read(1):
        return []
    return json.load(f)
def hands_truncate_write(f: io.FileIO, hands):
    hands = []
    for hand in hands:
        d = hand._asdict()
        d["team"] = d["team"].value
        d["suit"] = d["suit"].value
        hands.append(d)
    f.truncate()
    json.dump(hands, f)

def bid_file(f, bid):
    if bid == "s":
        click.echo("score")
    elif bid == "u":
        click.echo("undo")
    else:
        tpl = bid_parse(bid)
        if tpl:
            hands = hands_read(f)
            hands.append(tpl)
            score_print(hands)
            hands_truncate_write(f, hands)
        else:
            help_print()

# Command line calls cli
@click.command()
@click.option("-g", "--hands-file", default="hands.json", help="file name to store hands")
@click.argument("bid", nargs=1, required=False)
def cli(hands_file, bid):
    """score a collection of bridge hands USAGE:
    bridgepy [options] [bid]
    bid:  s (score), u (undo) or bid: w3sm3 - we 3 spade made 3, t2dd1 they 2 diamond down 1"""
    with open(hands_file, mode="w") as f:
        bid_file(f, bid)
