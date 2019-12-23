"""
Keep score in a game of bridge
"""
import click
import collections
import json
import fastapi
import enum
import io
from typing import (NamedTuple, List)
import time
import pathlib

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

class Result(NamedTuple):
    """Result of playing a hand.  It is using the enums which can not be converted to json so the methods
    to create a jsonable dictionary are provided"""
    team: Team
    bid: int
    suit: Suit
    over: int
    honors: Honors = Honors.NONE
    double: Double = Double.NONE
    def to_json_dictionary(self) -> dict:
        "Convert self to a jsonable dictionary"
        d = self._asdict()
        for k,v in Result.__annotations__.items():
            if isinstance(v, enum.EnumMeta):
                d[k] = d[k].value
        return d
    def from_json_dictionary(**hand_dict: dict) -> 'Result':
        "Create a Result from a jsonable dictionary"
        d = {}
        for k,v in hand_dict.items():
            enum_type = Result.__annotations__[k]
            if isinstance(enum_type, enum.EnumMeta):
                d[k] = enum_type(v)
            else:
                d[k] = v
        return Result(**d)

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
    "Print the score for a set of hands by converting them to rubbers and printing the rubbers"
    point_format = " {:3d} | {:3d}"
    we_total = 0
    they_total = 0
    rs = rubbers(hands)
    for r in rs:
        click.echo('  We | They')
        above_count = max(len(r.above[0]), len(r.above[1]))
        for i in range(above_count - 1, -1, -1):
            we = 0 if len(r.above[0]) <= i else r.above[0][i]
            they = 0 if len(r.above[1]) <= i else r.above[1][i]
            click.echo(point_format.format(we, they))
        click.echo("-------------")
        first_game = True
        for game in r.games:
            if first_game:
                first_game = False
            else:
                click.echo("- - - - - - -")
            score_count = max(len(game[0]), len(game[1]))
            for i in range(0, score_count):
                we = 0 if len(game[0]) <= i else game[0][i]
                they = 0 if len(game[1]) <= i else game[1][i]
                click.echo(point_format.format(we, they))
        click.echo("-------------")
        click.echo(point_format.format(r.total[0], r.total[1]))
        we_total += r.total[0]
        they_total += r.total[1]
        click.echo()
    if len(rs) > 1:
        # print total for all the rubbers
        click.echo("=================")
        click.echo("== All Rubbers ==")
        click.echo("=================")
        click.echo(point_format.format(we_total, they_total))

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

def rubbers(results: List[Result]) -> []:
    rubber = Rubber()
    ret = [rubber]
    for result in results:
        if rubber.add(result):
            rubber = Rubber()
            ret.append(rubber)
    return ret

def help_print():
    click.echo(cli.get_help(click.Context(cli)))

def hands_to_json_file(f: io.FileIO, hands):
    """write the hands array in json format to the file"""
    json.dump([hand.to_json_dictionary() for hand in hands], f)

def hands_from_json_file(f: io.FileIO) -> []:
    """Load a jso file and return the array of hands"""
    out = json.load(f)
    return [Result.from_json_dictionary(**hand_json) for hand_json in out]


def bid_file(hands_path, hands, bid):
    if bid == None:
        score_print(hands)
        return
    elif bid == "u":
        if len(hands) == 0:
            return
        hands.pop()
    else:
        tpl = bid_parse(bid)
        if tpl:
            hands.append(tpl)
        else:
            help_print()
            return
    with hands_path.open(mode="w") as f:
        hands_to_json_file(f, hands)
    score_print(hands)

def new_game_file(dir_str: str) -> pathlib.Path:
    file_name = time.strftime("%Y-%m-%d-%H-%M-%S") + ".json"
    directory = pathlib.Path(dir_str)
    file = directory / file_name
    if file.exists():
        raise FileExistsError()
    file.write_text("[]")
    return file
    
def existing_game_file(dir_str: str) -> pathlib.Path:
    directory = pathlib.Path(dir_str)
    paths = list(directory.glob("*-*-*-*-*-*.json"))
    if len(paths) == 0:
        raise FileNotFoundError()
    paths.sort()
    return paths[-1]

# Command line calls cli
@click.command()
@click.option("-d", "--directory", default=".", help="directory to store hands")
@click.option("-n", "--new-game", is_flag=True, help="start a new game, this will create a new file to store the hands")
@click.argument("bid", nargs=1, required=False)
def cli(directory, new_game, bid):
    """
    score a collection of bridge hands USAGE:
    bridgepy [options] [bid]
    bid -n; # start a new hand it will be named for the time
    bid w3sm3; # we 3 spade made 3
    bid t2dd1; # they 2 diamond down 1
    """
    run(directory, new_game, bid)

def run(directory, new_game, bid):
    hands_path = None
    if new_game:
        hands_path = new_game_file(directory)
    else:
        try:
            hands_path = existing_game_file(directory)
        except FileNotFoundError:
            hands_path = new_game_file(directory)

    try:
        with hands_path.open(mode="r") as f:
            hands = hands_from_json_file(f)
    except Exception:
        hands = []
    bid_file(hands_path, hands, bid)

#run(".", True, "w1sm1")