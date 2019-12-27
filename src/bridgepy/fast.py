import bridgepy
import fastapi
from starlette.responses import Response
import click
import pathlib
import uvicorn

app = fastapi.FastAPI()
hands = []

@app.get("/")
async def index():
    return Response(content=score())

@app.get("/hand")
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

def score():
    s = score_print(bridgepy.read_hands(bridgepy.existing_game_file(".")))
    return s
    #lines = s.split("\n")
    #return "<br>".join(lines)

def score_print(hands):
    "Print the score for a set of hands by converting them to rubbers and printing the rubbers"
    point_format = " {:4d} | {:4d}"
    we_total = 0
    they_total = 0
    rs = bridgepy.rubbers(hands)
    ret = ""
    for r in rs:
        ret += '  We  | They' + "\n"
        above_count = max(len(r.above[0]), len(r.above[1]))
        for i in range(above_count - 1, -1, -1):
            we = 0 if len(r.above[0]) <= i else r.above[0][i]
            they = 0 if len(r.above[1]) <= i else r.above[1][i]
            ret += point_format.format(we, they) + "\n"
        ret += "---------------" + "\n"
        first_game = True
        for game in r.games:
            if first_game:
                first_game = False
            else:
                ret += "- - - - - - - -" + "\n"
            score_count = max(len(game[0]), len(game[1]))
            for i in range(0, score_count):
                we = 0 if len(game[0]) <= i else game[0][i]
                they = 0 if len(game[1]) <= i else game[1][i]
                ret += point_format.format(we, they) + "\n"
        ret += "---------------" + "\n"
        ret += point_format.format(r.total[0], r.total[1]) + "\n"
        we_total += r.total[0]
        they_total += r.total[1]
    if len(rs) > 1:
        # print total for all the rubbers
        ret += "=================" + "\n"
        ret += "== All Rubbers ==" + "\n"
        ret += "=================" + "\n"
        ret += point_format.format(we_total, they_total) + "\n"
    return ret

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
