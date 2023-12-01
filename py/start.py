import webview
import argparse
import gameManager
import typing
import sys
import asyncio

parser = argparse.ArgumentParser()
parser.add_argument("-auto", "--auto", action="store_true", help="auto start")
parser.add_argument("-b", "--black", help="black player")
parser.add_argument("-w", "--white", help="white player")
args = parser.parse_args()


class Api:
    def __init__(self):
        pass

    def manualMove(self, row: int, col: int):
        game.dispatchManualMove(row, col)

    def getPlayerInfo(self) -> typing.Tuple[str, str]:
        return game.getInfo()

def tojsbool(b: bool):
    return "true" if b else "false"


def gameWin(player, wincode):
    reason = "Black Win\n" if player else "White Win\n"
    reason += "Reason: "
    match wincode:
        case 1:
            reason += "连成了五个"
        case 2:
            reason += "触发禁手"
        case 3:
            reason += "下在非空位置"
        case 4:
            reason += "超时"

    window.evaluate_js(f'gameWin(`{reason}`)')


def boardSetClickable(manualable: bool):
    window.evaluate_js(f"boardSetClickable({tojsbool(manualable)})")


def boardMakeMove(row, col, player):
    window.evaluate_js(f"boardMakeMove({row},{col},{tojsbool(player)})")



window = webview.create_window(
    "Gobang Bridge",
    "assets/index.html",
    js_api=Api(),
    width=1280,
    height=650,
    resizable=False,
    fullscreen=False,
    frameless=False,
    confirm_close=True,
)
game = gameManager.Game()

game.onGameWin = gameWin
game.onSetManualable = boardSetClickable
game.onMove = boardMakeMove

if args.black:
    game.createStdioPlayer(True, args.black)
else:
    game.createManualPlayer(True)
if args.white:
    game.createStdioPlayer(False, args.white)
else:
    game.createManualPlayer(False)


def start():
    game.start()
    window.evaluate_js("initialized()")


webview.start(start, debug=False)
