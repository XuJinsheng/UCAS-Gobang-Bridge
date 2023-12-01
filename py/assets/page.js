let enableBoardClick = true;
let lastMove = (0, 0), movecount = 0;
const STATE = {
	START: 0,
	PLAYINGBLACK: 1,
	PLAYINGWHITE: 2,
	WINBLACK: 3,
	WINWHITE: 4,
	END: 5
}

function getCellElement(row, col) {
	return document.getElementById(`cs${row}_${col}`);
}

function chesscellclicked(div, row, col) {
	if (!enableBoardClick)
		return;
	if (div.classList.contains("black") || div.classList.contains("white")) {
		return;
	}
	document.querySelector("#mannualcoordinateinput").value = "";
	sendBoardUserClick(row, col);
}
function coordinateclicked() {
	let str = document.querySelector("#mannualcoordinateinput").value;
	let m = /(\d{1,2}),(\d{1,2})/i.exec(str);
	if (m) {
		let row = parseInt(m[1]), col = parseInt(m[2]);
		let div = getCellElement(row, col);
		if (div.classList.contains("black") || div.classList.contains("white"))
			window.alert("这里已经有棋子了！");
		else chesscellclicked(div, row, col);
	} else {
		window.alert("无效输入");
	}

}
function boardSetClickable(clickable) {
	enableBoardClick = clickable;
	let board = document.getElementsByClassName("chessboard")[0];
	board.classList.toggle("chessboardclickable", clickable);
	document.querySelector("#mannualcoordinateinput").disabled = !clickable;
	document.querySelector("#coordinatebutton").disabled = !clickable;
}

function boardMakeMove(row, col, player) {
	getCellElement(lastMove[0], lastMove[1])?.classList.remove("lastmove");
	let cell = getCellElement(row, col);
	cell.classList.add(player ? "black" : "white");
	cell.classList.add("lastmove");
	lastMove = [row, col];

	movestr = String.fromCharCode(65 - 1 + row) + "" + (col);
	let recordtbody = document.querySelector("#recordtable>tbody");
	if (player) recordtbody.innerHTML += `<tr><td>${++movecount}</td><td>${movestr}</td><td></td></tr>`;
	else recordtbody.lastElementChild.lastElementChild.innerHTML = movestr;
	cell.innerHTML = movecount;//`<span style="text-align:center;">${movecount + 1}</span>`;
	let rtw = document.querySelector("#recordtable-wrapper");
	rtw.scrollTop = rtw.scrollHeight;

	document.getElementById("info-state").innerHTML = player ? "White's Turn" : "Black's Turn";
}


function gameWin(player, reason) {
	boardSetClickable(false);
	document.getElementById("info-state").innerHTML = reason;
}
function setPlayerInfo(blackplayer, whiteplayer) {
	document.getElementById("info-black").innerText = blackplayer;
	document.getElementById("info-white").innerText = whiteplayer;
}

function sendBoardUserClick(row, col) {
	pywebview.api.manualMove(row, col);
}

function initialized() {
	let div = document.getElementById("info-state");
	if (div.innerText == "Initializing")
		div.innerText = "Black's Turn";
}