import subprocess
from time import sleep
import typing
import os
import re
import asyncio
import threading


class Game:
    def __init__(self):
        self.board = [
            [0 for i in range(16)] for j in range(16)
        ]  # board: 2d array[row][col] 15*15(1-15), 0: empty, 1: black, -1: white
        self.black = None
        self.white = None

    onMove = None  # onMove(row, col, player)
    onGameWin = None  # onGameWin(player:bool, wincode:int)
    onSetManualable = None  # onSetManualable(bool)

    def createManualPlayer(self, player):
        assert player == True and not self.black or player == False and not self.white
        if player:
            self.black = ManualPlayer(self, True)
        else:
            self.white = ManualPlayer(self, False)

    def createStdioPlayer(self, player, cmd: str):
        assert (
            player == True
            and self.black == None
            or player == False
            and self.white == None
        )
        if player:
            self.black = StdioPlayer(self, True, cmd)
        else:
            self.white = StdioPlayer(self, False, cmd)

    def dispatchManualMove(self, row, col):
        if self.turn and type(self.black) == ManualPlayer:
            self.black.move(row, col)
        elif not self.turn and type(self.white) == ManualPlayer:
            self.white.move(row, col)

    def start(self):
        assert self.black and self.white
        self.turn = True
        self.white.start()
        self.black.start()

    def getInfo(self) -> typing.Tuple[str, str]:
        return (self.black.getInfo(), self.white.getInfo())

    def gameWin(self, player, wincode):  # wincode: 1: 连成五个，2：禁手，3：下在非空位置，4：超时
        if self.onGameWin:
            self.onGameWin(player, wincode)

    def makeMove(self, row, col, player):
        if player != self.turn:
            return
        self.log(player, row, col)
        if self.board[row][col] != 0:
            self.gameWin(not player, 3)
            return
        self.onMove(row, col, player)
        self.board[row][col] = 1 if player else -1
        if self.checkWin(row, col, player):
            self.gameWin(player, 1)
            return
        if self.turn == True and self.checkForbidden(row, col):
            self.gameWin(not player, 2)
            return
        self.turn = not self.turn
        (self.black if self.turn else self.white).enemyMove(row, col)

    def checkForbidden(self, row, col):
        pass

    def checkWin(self, row, col, player):
        pass

    def log(self, player, row, col):
        pass


class ManualPlayer:
    def __init__(self, game, player):
        self.game = game
        self.player = player

    def start(self):
        if self.player:
            self.game.onSetManualable(True)

    def enemyMove(self, row, col):
        if self.game.onSetManualable:
            self.game.onSetManualable(True)

    def move(self, row, col):
        if self.game.onSetManualable:
            self.game.onSetManualable(False)
        self.game.makeMove(row, col, self.player)

    def getInfo(self):
        return "ManualPlayer"


class StdioPlayer:
    def __init__(self, game, player, cmd):
        self.game = game
        self.player = player
        self.cmd = cmd
        self.initializing = True
        self.iolog = ""
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )

    def getInfo(self):
        retcode=self.process.poll()
        if retcode!=None:
            retcode= f"ExitCode:{retcode}\n"
        else :
            retcode="\n"
        return f"PID:{self.process.pid}{retcode}Cmdline:\n{self.cmd}"

    def writeStdin(self, data: bytes):
        self.process.stdin.write(data)
        self.process.stdin.flush()
        if type(data) == bytes:
            data = data.decode()
        self.iolog += "--------------%s--------------\n" % (data)

    def readlineStdout(self) -> str:
        data = self.process.stdout.readline()
        data = data.decode()
        self.iolog += data
        return data

    def start(self):
        while self.readlineStdout().strip().upper() != "READY":
            sleep(0.01)
        self.writeStdin(b"BLACK\n" if self.player else b"WHITE\n")
        self.initializing = False
        if self.player:
            asyncio.run(self.readMove())

    def enemyMove(self, row, col):
        self.writeStdin(b"MOVE(%d,%d)\n" % (row, col))
        asyncio.run(self.readMove())

    async def readMove(self):
        while True:
            s = self.readlineStdout().strip()
            m = re.match(r"MOVE.*?(\d{1,2}),(\d{1,2})", s, re.I)
            if m:
                self.game.makeMove(int(m.group(1)), int(m.group(2)), self.player)
                return
            sleep(0.01)
