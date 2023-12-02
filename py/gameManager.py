import subprocess
from time import sleep
import typing
import os
import re
import asyncio
import threading

# 用于检查禁手和胜利
class Checker:
	def __init__(self, board, recent_play, player):
		# recent_play: 最近落子位置
		# player: 落子玩家
		self.board = board
		self.recent_play = recent_play
		self.player = player
		self.mv_row = [1, 0, 1, 1]
		self.mv_col = [0, 1, 1,-1]

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
		# print(pos, res)
		return res
	
	def __dirSearch(self, pos, mv_r, mv_c):
		# 返回值(己方连子个数, 是否有遮挡, 涉及的棋子位置)
		line = set() # 最快的方式是使用zobrist hash算法计算棋子的hash值，但由于需要比较的次数不多，直接使用自带的set即可
		d = self.__maxStep(pos, mv_r, mv_c)
		print(pos, d)
		for i in range(1, d + 1):
			if self.board[pos[0] + i * mv_r][pos[1] + i * mv_c] != self.player:
				return (i - 1, 1, line) if self.board[pos[0] + i * mv_r][pos[1] + i * mv_c] == -self.player else (i - 1, 0, line)
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
					if self.board[self.recent_play[0] + i * mv_r][self.recent_play[1] + i * mv_c] == 0:
						res = self.__lineDetect((self.recent_play[0] + i * mv_r, self.recent_play[1] + i * mv_c), dir)
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
		
class Game:
	def __init__(self):
		self.board = [
			[0 for i in range(16)] for j in range(16)
		]  # board: 2d array[row][col] 15*15(1-15), 0: empty, 1: black, -1: white
		# 为什么要用1~15的下标啊？？？
		self.black = None
		self.white = None
	def __del__(self):
		if self.black:
			del self.black
		if self.white:
			del self.white
	onMove = None  # onMove(row, col, player)
	onGameWin = None  # onGameWin(player:bool, wincode:int)
	onSetManualable = None  # onSetManualable(bool)

	@staticmethod
	def __cvtPlayer(player):
		# 用于进行player(1/0)与棋盘标记(1/-1)的转换
		return 1 if player else -1
	
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
		self.board[row][col] = self.__cvtPlayer(player)
		if self.checkWin(row, col, player):
			self.gameWin(player, 1)
			return
		if self.turn == True and self.checkForbidden(row, col, player):
			self.gameWin(not player, 2)
			return
		self.turn = not self.turn
		(self.black if self.turn else self.white).enemyMove(row, col)

	def checkForbidden(self, row, col, player):
		checker = Checker(self.board, (row, col), self.__cvtPlayer(player))
		return checker.checkThreeFour()

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
		
	def __del__(self):
		self.process.kill()

	def getInfo(self):
		retcode=self.process.poll()
		if retcode!=None:
			retcode= f"ExitCode:{retcode}\n"
		else :
			retcode=""
		return f"PID:{self.process.pid}\n{retcode}Cmdline:\n{self.cmd}"

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
