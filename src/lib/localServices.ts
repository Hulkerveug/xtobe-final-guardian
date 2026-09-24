const MEMORY_KEY = "xtobe.guardian.memory";
const TASK_KEY = "xtobe.guardian.tasks";
import type { MemoryEntry, TaskRecord } from "../types";

export const memoryService = {
  recall(): MemoryEntry[] {
    try { return JSON.parse(localStorage.getItem(MEMORY_KEY) ?? "[]") as MemoryEntry[]; } catch { return []; }
  },
  learn(type: MemoryEntry["type"], message: string): MemoryEntry[] {
    const entries = [{ timestamp: new Date().toISOString(), type, message }, ...this.recall()].slice(0, 200);
    localStorage.setItem(MEMORY_KEY, JSON.stringify(entries));
    return entries;
  },
};

export const taskService = {
  add(command: string): TaskRecord {
    const tasks = this.list();
    const task: TaskRecord = { id: crypto.randomUUID(), command, status: "queued", createdAt: new Date().toISOString() };
    localStorage.setItem(TASK_KEY, JSON.stringify([task, ...tasks].slice(0, 100)));
    return task;
  },
  list(): TaskRecord[] {
    try { return JSON.parse(localStorage.getItem(TASK_KEY) ?? "[]") as TaskRecord[]; } catch { return []; }
  },
};

export const gitService = {
  status(): "clean" | "local-changes" | "unavailable" {
    return "local-changes";
  },
};
