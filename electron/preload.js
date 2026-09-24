import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("xtobeGuardian", Object.freeze({
  activate: (message) => ipcRenderer.invoke("guardian:activate", { message }),
}));
