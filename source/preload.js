const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
	boardUserClick: (row, col) => ipcRenderer.send('board-user-click', row, col),
	boardMakeMove: (callback) => ipcRenderer.on('board-make-move', callback),
	boardSetClickable: (callback) => ipcRenderer.on('board-set-clickable', callback),
	gameWin: (callback) => ipcRenderer.on('game-win', callback),
	setPlayerInfo:(callback)=>ipcRenderer.on('set-player-info',callback),
})