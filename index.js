const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let win;

function createWindow() {
    win = new BrowserWindow({
        width: 800,
        height: 600,
        webPreferences: {
            nodeIntegration: false,  // Disable Node.js integration for security
            preload: path.join(__dirname, 'preload.js'),  // Preload script
        }
    });

    win.loadURL('http://localhost:5000');  // Load the Flask server or your frontend

    // Listen for 'run-python' messages from renderer
    ipcMain.on('run-python', (event, arg) => {
        const python = spawn('python', [path.join(__dirname, 'app.py')]);

        python.stdout.on('data', (data) => {
            console.log(`Python Output: ${data}`);
            event.reply('python-output', data.toString());  // Send data back to renderer
        });

        python.stderr.on('data', (data) => {
            console.error(`Python Error: ${data}`);
        });

        python.on('close', (code) => {
            console.log(`Python script finished with code ${code}`);
        });
    });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

