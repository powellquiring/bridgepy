"""
Keep score in a game of bridge
"""
import click
import json
import collections
import enum
from typing import List
from bridgepy import *

STORAGE_FILE = "file"
STORAGE_COS = "cos"
ROOT = "pfq-bridgepy"
# COS_INSTANCE_ID="crn:v1:bluemix:public:cloud-object-storage:global:a/713c783d9a507a53135fe6793c37cc74:816ac7d3-10f7-4b06-a7bc-570da47b4c0b::"
COS_INSTANCE_ID = "crn:v1:bluemix:public:cloud-object-storage:global:a/713c783d9a507a53135fe6793c37cc74:eefa2d30-edb6-4105-ac49-2a66ff0de075::"
COS_SERVICE_ENDPOINT = "https://s3-api.us-geo.objectstorage.softlayer.net"
ENV_PREFIX = "BRIDGEPY"


def honors_double(s):
    if s == "d":
        return {"double": Double.DOUBLE}
    elif s == "r":
        return {"double": Double.REDOUBLE}
    elif s == "0":
        return {"honors": Honors.H100}
    elif s == "5":
        return {"honors": Honors.H150}
    else:
        raise Exception("Honors or double must be d, r, 0, 5 but was", s)


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
    team = Team.WE if bid[0] == "w" else Team.THEY
    bid_tricks = int(bid[1])
    suit = Suit(bid[2])
    made_or_down = bid[3]
    over_tricks = int(bid[4])
    over_tricks = -over_tricks if made_or_down == "d" else over_tricks - bid_tricks
    ret = Result(team, bid_tricks, suit, over_tricks)
    for indx in range(5, len(bid)):
        ret = ret._replace(**honors_double(bid[indx]))
    return ret


def score_print(hands: List[Result]):
    "Print the score for a set of hands by converting them to rubbers and printing the rubbers"
    click.echo(score_str(hands))


def add_nl(s: str) -> str:
    return s + "\n"


def score_str(hands: List[Result]) -> str:
    "generate a string score for a set of hands by converting them to rubbers and printing the rubbers"
    ret = ""
    point_format = " {:3d} | {:3d}"
    we_total = 0
    they_total = 0
    rs = rubbers(hands)
    for r in rs:
        ret += add_nl("  We | They")
        above_count = max(len(r.above[0]), len(r.above[1]))
        for i in range(above_count - 1, -1, -1):
            we = 0 if len(r.above[0]) <= i else r.above[0][i]
            they = 0 if len(r.above[1]) <= i else r.above[1][i]
            ret += add_nl(point_format.format(we, they))
        ret += add_nl("-------------")
        first_game = True
        for game in r.games:
            if first_game:
                first_game = False
            else:
                ret += add_nl("- - - - - - -")
            score_count = max(len(game[0]), len(game[1]))
            for i in range(0, score_count):
                we = 0 if len(game[0]) <= i else game[0][i]
                they = 0 if len(game[1]) <= i else game[1][i]
                ret += add_nl(point_format.format(we, they))
        ret += add_nl("-------------")
        ret += add_nl(point_format.format(r.total[0], r.total[1]))
        we_total += r.total[0]
        they_total += r.total[1]
        ret += add_nl("")
    if len(rs) > 1:
        # print total for all the rubbers
        ret += add_nl("=================")
        ret += add_nl("== All Rubbers ==")
        ret += add_nl("=================")
        ret += add_nl(point_format.format(we_total, they_total))
    return ret


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
        self.above = [[], []]  # we and they list above the line
        self.games = [
            [[], []]
        ]  # games below the line, list of games, each game has a list of contracts won for We and They
        self.games_won = [0, 0]  # we, they games won
        self.total = [0, 0]  # we and they totals

    def complete(self):
        return (
            self.games_won[Team.WE.value] == 2 or self.games_won[Team.THEY.value] == 2
        )

    def add(self, result: Result) -> bool:
        """add the result to the rubber return True if the rubber is now complete"""
        if self.complete():
            raise Exception("Can not add to this Rubber, is is complete")
        contract_winner = result.team.value
        contract_loser = 1 - contract_winner
        vulnerable = self.games_won[contract_winner] == 1
        if result.over >= 0:  # made contract
            above_points = []  # apoints earned above the line for this hand
            last_game = self.games[len(self.games) - 1]
            trick_value = (
                20 if result.suit == Suit.DIAMOND or result.suit == Suit.CLUB else 30
            )
            under_points = trick_value * result.bid * result.double.value
            under_points += 10 if result.suit == Suit.NOTRUMP else 0
            last_game[contract_winner].append(under_points)
            if result.over > 0:
                over_trick_points = 0
                if result.double == Double.NONE:
                    over_trick_points = trick_value * result.over * result.double.value
                else:
                    over_trick_points = (
                        50
                        * result.over
                        * result.double.value
                        * (2 if vulnerable else 1)
                    )
                above_points.append(over_trick_points)
            slam_bonus = 0
            if result.bid == 6:
                slam_bonus = 750 if vulnerable else 500
            if result.bid == 7:
                slam_bonus = 1000 if vulnerable else 1500
            if slam_bonus:
                above_points.append(slam_bonus)
            if result.double != Double.NONE:
                above_points.append(
                    50 if result.double == Double.DOUBLE else 100
                )  # insult
            if result.honors != Honors.NONE:
                above_points.append(result.honors.value)
            if sum(last_game[contract_winner]) >= 100:
                self.games_won[
                    contract_winner
                ] += 1  # keep track of games won for each team
                if self.complete():
                    rubber_bonus = 700 if self.games_won[contract_loser] == 0 else 500
                    above_points.append(rubber_bonus)
                else:
                    self.games.append([[], []])  # add a new game

            self.above[contract_winner].extend(above_points)
            self.total[contract_winner] += under_points
            self.total[contract_winner] += sum(above_points)
        else:  # set
            #          vu   vd      vr   nu  nd      nr
            trick1 = [
                100,
                200,
                0,
                400,
                50,
                100,
                0,
                200,
            ]  # vulnerable undoubled, doubled, redoubled, not vulnerable, ...
            trick23 = [
                100,
                300,
                0,
                600,
                50,
                200,
                0,
                400,
            ]  # vulnerable undoubled, doubled, redoubled, not vulnerable, ...
            trick4 = [
                100,
                300,
                0,
                600,
                50,
                300,
                0,
                600,
            ]  # vulnerable undoubled, doubled, redoubled, not vulnerable, ...
            set_tricks = -result.over
            point_index = (
                4 * (0 if vulnerable else 1) + result.double.value - 1
            )  # double value is 1, 2, 4
            set_points = trick1[point_index]  # first set trick
            set_tricks -= 1
            for i in range(0, set_tricks if set_tricks <= 2 else 2):
                set_points += trick23[point_index]
                set_tricks -= 1
            for i in range(0, set_tricks):
                set_points += trick4[point_index]
            self.above[contract_loser].append(set_points)
            self.total[contract_loser] += set_points
        return self.complete()


def rubbers(results: List[Result]) -> List[Rubber]:
    rubber = Rubber()
    ret = [rubber]
    for result in results:
        if rubber.add(result):
            rubber = Rubber()
            ret.append(rubber)
    return ret


def help_print():
    click.echo(cli.get_help(click.Context(cli)))


def bid_and_store(results_storeage, hands, bid):
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
    results_storeage.store_results(hands)
    score_print(hands)


def function_call_get_score(**kwargs):
    result_storage = ResultsCOS(
        kwargs["root"],
        kwargs["api_key"],
        kwargs["cos_instance_id"],
        kwargs["cos_service_endpoint"],
    )
    hands = result_storage.existing_results()
    return score_str(hands)


def run(root, new_game, storage, api_key, instance_id, cos_service_endpoint, bid):
    print(root, new_game, storage, api_key, instance_id, cos_service_endpoint, bid)
    if storage == STORAGE_FILE:
        result_storage = ResultsFile(root)
    else:
        result_storage = ResultsCOS(root, api_key, instance_id, cos_service_endpoint)

    if new_game:
        hands = result_storage.new_results()
    else:
        hands = result_storage.existing_results()
    bid_and_store(result_storage, hands, bid)


# Command line calls cli
@click.command()
@click.option(
    "-n",
    "--new-game",
    is_flag=True,
    help="start a new game, this will create a new file to store the hands",
)
@click.option("--file", "storage", flag_value=STORAGE_FILE)
@click.option("--cos", "storage", flag_value=STORAGE_COS, default=True)
@click.option("-k", "--api-key", help="ibm cloud api key,  needed for COS")
@click.option("-r", "--root", help="cos bucket or root directory")
@click.option("--root-test", help="cos bucket or root test directory")
@click.option("-i", "--cos-instance-id", help="ibm cloud instance id, needed for COS")
@click.option("-e", "--cos-service_endpoint", help="COS service endpoint")
@click.option(
    "-p",
    "--print-params",
    is_flag=True,
    default=False,
    help="print parameters and exit, useful for testing",
)
@click.option(
    "-f",
    "--simulate-function",
    is_flag=True,
    default=False,
    help="simulate the call that the cloud function makes",
)
@click.argument("bid", nargs=1, required=False)
def click_cli(
    root,
    root_test,
    new_game,
    storage,
    api_key,
    cos_instance_id,
    cos_service_endpoint,
    bid,
    print_params,
    simulate_function,
):
    """
    score a collection of bridge hands USAGE:
    bridgepy [options] [bid]
    bid -n; # start a new hand it will be named for the time
    bid w3sm3; # we 3 spade made 3
    bid t2dd1; # they 2 diamond down 1
    """
    if print_params:
        click.echo(
            json.dumps(
                {
                    "root": root,
                    "root_test": root_test,
                    "new_game": new_game,
                    "storage": storage,
                    "api_key": api_key,
                    "cos_instance_id": cos_instance_id,
                    "cos_service_endpoint": cos_service_endpoint,
                    "print_params": print_params,
                    "simulate_function": simulate_function,
                    "bid": bid,
                }
            )
        )
        return
    if simulate_function:
        function_call_get_score(**d)
    else:
        run(
            root, new_game, storage, api_key, cos_instance_id, cos_service_endpoint, bid
        )


def cli():
    click_cli(auto_envvar_prefix=ENV_PREFIX)


if __name__ == "__main__":
    cli()
