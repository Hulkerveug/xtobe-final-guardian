import { app, BrowserWindow, ipcMain } from "electron";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

function createWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 800,
    frame: true,
    backgroundColor: "#020403",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      preload: path.join(__dirname, "preload.js"),
    },
  });
  window.removeMenu();
  window.loadFile(path.join(__dirname, "index.html"));
}

ipcMain.handle("guardian:activate", (_event, payload) => ({
  ok: true,
  activatedAt: new Date().toISOString(),
  message: String(payload?.message ?? "Guardian activation requested").slice(0, 500),
}));

app.whenReady().then(() => {
  createWindow();
  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
