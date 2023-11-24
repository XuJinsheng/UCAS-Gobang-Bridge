"use strict"

const { app, BrowserWindow, Menu, ipcMain, shell } = require('electron');
const process = require('node:process');
const child_process = require('node:child_process');
const path = require('path')
const commander = require('commander');

function initApplication() {
	Menu.setApplicationMenu(null);
	mainWindow = new BrowserWindow({
		width: 1280,
		height: 650,
		webPreferences: {
			preload: path.join(__dirname, 'preload.js')
		}
	});
	mainWindow.loadFile('index.html');
	//mainWindow.webContents.openDevTools();
	setInterval(sendPlayerInfo, 1000);
	setTimeout(initPlayer, 500);
}

app.whenReady().then(() => { initApplication(); })
app.on('window-all-closed', () => { app.quit(); })

function sendBoardSetClickable(clickable) { mainWindow.webContents.send('board-set-clickable', clickable); }
function sendBoardMakeMove(row, col, player) { mainWindow.webContents.send('board-make-move', row, col, player) };




let mainWindow;
let blackplayer, whiteplayer;
let board = new Array(16);// 0:empty 1:black -1:white
for (let i = 1; i < 16; i++) { board[i] = new Array(16); for (let j = 1; j < 16; j++) board[i][j] = 0; }
let turns = true; let turnscount = 0;


function sendPlayerInfo() { mainWindow.webContents.send('set-player-info', blackplayer?.getInfo(), whiteplayer?.getInfo()); }
ipcMain.on('board-user-click', (event, row, col) => {
	if (blackplayer.myturn)
		blackplayer.onMove(row, col);
	else if (whiteplayer.myturn)
		whiteplayer.onMove(row, col);
});



function initPlayer() {
	let argv = process.argv;
	argv.splice(1, 0, "-auto");
	commander.version('0.0.1')
		.option('-b, --black [black]', 'Black Player', 'user')
		.option('-w, --white [white]', 'White Player', "user")
		.option("-cwd, --cwd [cwd]", "Working Directory", process.cwd())
		.option('-auto, --auto', 'Auto Start', true)
		.parse(process.argv);
	let opts = commander.opts();
	if (opts.cwd) process.chdir(opts.cwd);
	if (opts.black == undefined || opts.black == "user" || opts.black == true) blackplayer = new ManualPlayer(true);
	else blackplayer = new StdioPlayer(true, opts.black);
	if (opts.white == undefined || opts.white == "user" || opts.white == true) whiteplayer = new ManualPlayer(false);
	else whiteplayer = new StdioPlayer(false, opts.white);
	//if (opts.auto) {
	blackplayer.start();
	whiteplayer.start();
	//}
}

// type: 1: 连成五个，2：禁手，3：下在非空位置，4：超时
function gameWin(player, type) {
	let reason = "Reason:"
	switch (type) {
		case 1: reason += "连成了五个"; break;
		case 2: reason += "触发禁手"; break;
		case 3: reason += "下在非空位置"; break;
		case 4: reason += "超时"; break;
	}
	mainWindow.webContents.send('game-win', player, reason);
	console.log(player ? "Black Wins" : "White Wins");
	console.log(reason);
}
function makemove(row, col, player) {
	function checkWin(row, col, player) {
		let count = 0;
		for (let i = row - 4; i <= row + 4; i++) {
			if (i < 1 || i > 15) continue;
			if (board[i][col] == (player ? 1 : -1)) count++;
			else count = 0;
			if (count == 5) return true;
		}
		count = 0;
		for (let i = col - 4; i <= col + 4; i++) {
			if (i < 1 || i > 15) continue;
			if (board[row][i] == (player ? 1 : -1)) count++;
			else count = 0;
			if (count == 5) return true;
		}
		count = 0;
		for (let i = -4; i <= 4; i++) {
			if (row + i < 1 || row + i > 15 || col + i < 1 || col + i > 15) continue;
			if (board[row + i][col + i] == (player ? 1 : -1)) count++;
			else count = 0;
			if (count == 5)
				return true;
		}
		count = 0;
		for (let i = -4; i <= 4; i++) {
			if (row + i < 1 || row + i > 15 || col - i < 1 || col - i > 15) continue;
			if (board[row + i][col - i] == (player ? 1 : -1)) count++;
			else count = 0;
			if (count == 5) return true;
		}
		return false;
	}
	function checkBlanceRule(row, col) {
		return false;
	}

	if (player != turns) return;
	let stepstr = String.fromCharCode(65 - 1 + row) + "" + (col);
	if (turns) {
		turnscount++;
		process.stdout.write(`Step ${turnscount}: stepstr `);
	} else {
		process.stdout.write(` ${stepstr}\n`);
	}

	if (board[row][col] != 0) {
		gameWin(!player, 3);
		return;
	}

	board[row][col] = turns ? 1 : -1;
	sendBoardMakeMove(row, col, turns);
	if (checkWin(row, col, turns)) {
		gameWin(turns, 1);
		return;
	}
	if (player == true && checkBlanceRule(row, col)) {
		gameWin(false, 2);
	}

	turns = !turns;
	(turns ? blackplayer : whiteplayer).sendEnemyMove(row, col);
}




class ManualPlayer {
	player = false;
	myturn = false;
	constructor(player) {
		this.player = player;
		this.myturn = player;
	}
	start() {
		if (this.player)
			sendBoardSetClickable(true);
	}
	sendEnemyMove(row, col) {
		this.myturn = true;
		sendBoardSetClickable(true);
	}
	onMove(row, col) {
		this.myturn = false;
		sendBoardSetClickable(false);
		makemove(row, col, this.player);
	}
	getInfo() {
		return "Manual Player";
	}
}

class StdioPlayer {
	constructor(player, cmdline) {
		this.exePath = cmdline;
		this.player = player;
		this.myturn = this.player;
		this.lastline = "";
		this.logstdoutstr = "";
		this.lastinput = "";
		this.initfinish = false;
		this.process = child_process.exec(cmdline);
		this.process.stdout.on('data', this.onData.bind(this));
		this.process.stderr.on('data', (data) => {
			console.error(`${this.player ? "Black player" : "White player"} stderr: ${data}`);
		});
		this.process.on('close', (code) => {
			console.log(`${this.player ? "Black player" : "White player"} process exited with code ${code}`);
		});
	}
	logstdout(data) {
		this.logstdoutstr += data;
	}
	onData(data) {
		this.logstdout(data);
		for (let i = 0; i < data.length; i++) {
			if (data[i] == '\n') {
				this.parseOutput(this.lastline);
				this.lastline = "";
			} else {
				this.lastline += data[i];
			}
		}
	}
	parseOutput(str) {
		str = str.toLowerCase().trim();
		if (str == "") return;
		if (!this.initfinish && str.includes("readytogetplayer")) {
			this.initfinish = true;
			this.process.stdin.write(`${this.player ? "Black" : "White"}\n`);
			// alert
			if (this.lastinput) this.process.stdin.write(this.lastinput);
			return;
		}
		if (this.myturn) {
			let m = /step.*?(\d{1,2}),(\d{1,2})/i.exec(str);
			if (m) this.onMove(parseInt(m[1]), parseInt(m[2]));
		}
	}
	start() {
	}
	sendEnemyMove(row, col) {
		this.myturn = true;
		if (this.initfinish) this.process.stdin.write(`step(${row},${col})\n`);
		else this.lastinput += `${row},${col}\n`;
	}
	onMove(row, col) {
		this.myturn = false;
		makemove(row, col, this.player);
	}
	getInfo() {
		return `Command Line: \n${this.exePath}${this.initfinish ? "" : "\nInfo: Initializing"}`;
	}
}

/*
const FFI = require('ffi-napi');
class DllPlayer {
	constructor(player, dllpath) {
		this.dllpath = dllpath;
		this.player = player;
		this.lib = FFI.Library(dllpath, {
			"setPlayer": ["int", ["int"]],
			"sendMove": ["int", ["int", "int"]]
		});
	}
	start() {
		this.lib.setPlayer.async(this.player ? 1 : -1, (err, ret) => {
			if (this.player) this.onMove(ret >> 16, ret & 0xffff);
		});
	}
	sendEnemyMove(row, col) {
		this.lib.sendMove.async(row, col, (err, ret) => {
			if (err) console.error(err);
			else this.onMove(ret >> 16, ret & 0xffff);
		});
	}
	onMove(row, col) {
		makemove(row, col, this.player);
	}
	getInfo() {
		return `DLL Path: \n${this.dllpath}`;
	}
}
/*
const REF = require("ref");
const FFI = require("ffi");
const IntPtr = REF.refType(REF.types.int);
class DllPlayer {
	constructor(player, dllpath) {
		this.dllpath = dllpath;
		this.player = player;
		this.lib = FFI.Library(dllpath, {
			"setPlayer": ["void", ["int", IntPtr, IntPtr]],
			"sendMove": ["void", ["int", "int", IntPtr, IntPtr]]
		});
		this.rowptr = REF.alloc(REF.types.int);
		this.colptr = REF.alloc(REF.types.int);
	}
	start() {
		this.lib.setPlayer.async(this.player ? 1 : -1, this.rowptr, this.colptr, (err, ret) => {
			if (this.player) this.onMove(this.rowptr.deref(), this.colptr.deref());
		});
	}
	sendEnemyMove(row, col) {
		this.lib.sendMove.async(row, col, this.rowptr, this.colptr, (err, ret) => {
			if (err) console.error(err);
			else this.onMove(this.rowptr.deref(), this.colptr.deref());
		});
	}
	onMove(row, col) {
		makemove(row, col, this.player);
	}
	getInfo() {
		return `DLL Path: \n${this.dllpath}`;
	}
}*/
