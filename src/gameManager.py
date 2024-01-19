import subprocess
from time import sleep
import typing
import os
import re
import json
from concurrent.futures import ThreadPoolExecutor

threadPool = ThreadPoolExecutor()


WINREASON = [
    "Still Playing",
    "Five in a row",
    "Forbidden",
    "Non-empty position",
    "Draw",
    "Timeout",
]
FORBIDDENRULE = ["Off", "On"]


class Checker:
    def __init__(self):
        self.board = [
            [0 for i in range(16)] for j in range(16)
        ]  # board: 2d array[row][col] 15*15(1-15), 0: empty, 1: black, -1: white
        self.mv_row = [1, 0, 1, 1]
        self.mv_col = [0, 1, 1, -1]

    def __getitem__(self, item):
        row, col = item
        return self.board[row][col]

    def makemove(self, row, col, player: bool):
        self.board[row][col] = 1 if player else -1
        self.recent_play = (row, col)
        self.player = 1 if player else -1

    def __maxStep(self, pos, mv_r, mv_c):
        # pos : (row_num, col_num)
        dr = 15
        dc = 15
        if mv_r != 0:
            dr = 15 - pos[0] if mv_r == 1 else pos[0] - 1
        if mv_c != 0:
            dc = 15 - pos[1] if mv_c == 1 else pos[1] - 1
        return min(dr, dc)

    def __lineDetect(self, pos, dir):
        # 返回值同__dirSearch，但考虑了两个方向
        res1 = self.__dirSearch(pos, self.mv_row[dir], self.mv_col[dir])
        res2 = self.__dirSearch(pos, -self.mv_row[dir], -self.mv_col[dir])
        res = (res1[0] + res2[0], res1[1] | res2[1], res1[2] | res2[2])
        return res

    def __dirSearch(self, pos, mv_r, mv_c):
        # 返回值(己方连子个数, 是否有遮挡, 涉及的棋子位置)
        line = set()  # 最快的方式是使用zobrist hash算法计算棋子的hash值，但由于需要比较的次数不多，直接使用自带的set即可
        d = self.__maxStep(pos, mv_r, mv_c)
        for i in range(1, d + 1):
            if self.board[pos[0] + i * mv_r][pos[1] + i * mv_c] != self.player:
                return (
                    (i - 1, 1, line)
                    if self.board[pos[0] + i * mv_r][pos[1] + i * mv_c] == -self.player
                    else (i - 1, 0, line)
                )
            line.add((pos[0] + i * mv_r, pos[1] + i * mv_c))
        return (d, 1, line)

    @staticmethod
    def __countWithoutDuplication(lst):
        newLst = []
        for elem in lst:
            if elem not in newLst:
                newLst.append(elem)
        return len(newLst)

    def checkThreeFour(self):
        three = []
        four = []
        for dir in range(4):
            for p in [-1, 1]:
                mv_r = p * self.mv_row[dir]
                mv_c = p * self.mv_col[dir]
                d = self.__maxStep(self.recent_play, mv_r, mv_c)
                for i in range(1, d + 1):
                    if (
                        self.board[self.recent_play[0] + i * mv_r][
                            self.recent_play[1] + i * mv_c
                        ]
                        == 0
                    ):
                        res = self.__lineDetect(
                            (
                                self.recent_play[0] + i * mv_r,
                                self.recent_play[1] + i * mv_c,
                            ),
                            dir,
                        )
                        if res[0] == 3 and res[1] == 0:
                            three.append(res[2])
                        elif res[0] == 4:
                            four.append(res[2])
                        break
        threeCnt = self.__countWithoutDuplication(three)
        fourCnt = self.__countWithoutDuplication(four)
        if threeCnt >= 2 or fourCnt >= 2:
            return True
        return False

    def checkFive(self):
        # 返回值：2->长连, 1->连5, 0->无
        maxl = 0
        for dir in range(4):
            res = self.__lineDetect(self.recent_play, dir)
            if res[0] > 4:
                return 2
            maxl = max(maxl, res[0])
        if maxl == 4:
            return 1
        return 0


class Game:
    def __init__(self, forbidden):
        self.board = Checker()
        self.black = None
        self.white = None
        self.forbidden = forbidden
        self.stepcount = 0

        self.moveLog = []
        self.winCode = 0
        self.winPlayer = None
        self.onMove = None  # onMove(row, col, player)
        self.onGameWin = None  # onGameWin(player:bool, wincode:int)
        self.onSetManualable = None  # onSetManualable(bool)

    def close(self):
        global threadPool
        if self.black:
            self.black.close()
            self.black = None
        if self.white:
            self.white.close()
            self.white = None
        threadPool.shutdown(wait=True, cancel_futures=True)
        threadPool = ThreadPoolExecutor()

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

    def getPlayerInfo(self) -> typing.Tuple[str, str]:
        if self.black and self.white:
            return (self.black.getInfo(), self.white.getInfo())
        return ("", "")

    def getIOlog(self) -> typing.Tuple[str, str]:
        blacklog = ""
        whitelog = ""
        if type(self.black) == StdioPlayer:
            blacklog = self.black.iolog_unstaged
            self.black.iolog_unstaged = ""
        if type(self.white) == StdioPlayer:
            whitelog = self.white.iolog_unstaged
            self.white.iolog_unstaged = ""
        return (blacklog, whitelog)

    def gameWin(self, player, wincode):  # wincode: 1: 连成五个，2：禁手，3：下在非空位置，4：平局, 5: 超时
        self.winPlayer = player
        self.winCode = wincode
        if self.onGameWin:
            self.onGameWin(player, wincode)

    def makeMove(self, row, col, player: bool):
        if player != self.turn:
            return
        self.stepcount += 1
        self.logMove(player, row, col)
        if self.board[row, col] != 0:
            self.gameWin(not player, 3)
            return
        self.onMove(row, col, player)
        self.board.makemove(row, col, player)
        if not player:
            if self.board.checkFive() >= 1:
                self.gameWin(player, 1)
                return
        else:
            match self.forbidden:
                case 0:
                    if self.board.checkFive() >= 1:
                        self.gameWin(player, 1)
                        return
                case 1:
                    if self.board.checkFive() == 1:
                        self.gameWin(player, 1)
                        return
                    if self.board.checkFive() == 2 or self.board.checkThreeFour():
                        self.gameWin(not player, 2)
                        return

        if self.stepcount == 19 * 19:
            self.gameWin(False, 4)
        self.turn = not self.turn
        (self.black if self.turn else self.white).enemyMove(row, col)

    def logMove(self, player, row, col):
        self.moveLog.append((player, row, col))

    def saveLog(self, filepath, append=False):
        log = {
            "ForbiddenRule": FORBIDDENRULE[self.forbidden],
            "WinPlayer": self.winPlayer,
            "Wincode": WINREASON[self.winCode],
            "Black": self.black.getInfoDict(),
            "White": self.white.getInfoDict(),
            "MoveLog": self.moveLog,
        }
        if append:
            with open(filepath, "r+") as f:
                origin = json.load(f)
                origin.append(log)
                f.seek(0)
                json.dump(origin, f)
        else:
            with open(filepath, "w") as f:
                json.dump([log], f)


class ManualPlayer:
    def __init__(self, game, player):
        self.game = game
        self.player = player

    def close(self):
        pass

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

    def getInfoDict(self):
        return "ManualPlayer"


class StdioPlayer:
    def __init__(self, game, player, cmd):
        self.game = game
        self.player = player
        self.cmd = cmd
        self.initializing = True
        self.iolog = ""
        self.iolog_unstaged = ""
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            shell=False,
        )

    def close(self):
        self.process.kill()
        self.process = None

    def getInfo(self):
        retcode = self.process.poll()
        if retcode != None:
            retcode = f"ExitCode:{retcode}\n"
        else:
            retcode = ""
        return f"PID:{self.process.pid}\n{retcode}Cmdline:\n{self.cmd}"

    def getInfoDict(self):
        return {
            "PID": self.process.pid,
            "CmdLine": self.cmd,
            "ExitCode": self.process.poll(),
        }

    def writeStdin(self, data: bytes):
        self.process.stdin.write(data)
        self.process.stdin.flush()
        if type(data) == bytes:
            data = data.decode()
        self.iolog += "--------------%s" % (data)
        self.iolog_unstaged += "--------------%s" % (data)

    def readlineStdout(self) -> str:
        data = self.process.stdout.readline()
        # guess encoding
        try:
            data = data.decode("utf-8")
        except UnicodeDecodeError:
            data = data.decode("gbk")
        self.iolog += data
        self.iolog_unstaged += data
        return data

    def start(self):
        while self.readlineStdout().strip().upper() != "READY":
            sleep(0.01)
        self.writeStdin(b"BLACK\n" if self.player else b"WHITE\n")
        self.initializing = False
        if self.player:
            threadPool.submit(self.readMove)

    def enemyMove(self, row, col):
        #self.writeStdin(b"MOVE(%d,%d)\n" % (row, col))
        self.writeStdin(b"MOVE %c%d\n" % (ord("A") + col - 1, row))
        threadPool.submit(self.readMove)

    def readMove(self):
        sleep(0.2)
        while True:
            s = self.readlineStdout().strip()
            m = re.match(r"MOVE.*?(\d{1,2}),(\d{1,2})", s, re.I)
            if m == None:
                m = re.match(r"MOVE.*?([a-z])(\d{1,2})", s, re.I)
            if m:
                if m.group(1).isalpha():
                    col = ord(m.group(1).upper()) - ord("A") + 1
                    row = int(m.group(2))
                else:
                    row = int(m.group(1))
                    col = int(m.group(2))
                self.game.makeMove(row, col, self.player)
                return
            sleep(0.01)
