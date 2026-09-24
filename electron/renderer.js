const button = document.querySelector("#activate");
const status = document.querySelector("#status");
const consoleBox = document.querySelector("#console");

button.addEventListener("click", async () => {
  button.disabled = true;
  status.textContent = "SYSTEM ACTIVATING";
  consoleBox.textContent += "\n> VIBRANIUM CORE ....... ONLINE";
  consoleBox.textContent += "\n> GUARDIAN THONE ....... AWAKENING";
  try {
    const result = await window.xtobeGuardian.activate("ACTIVATE GUARDIAN");
    if (result?.ok) {
      button.textContent = "GUARDIAN ACTIVE";
      status.textContent = "SYSTEM AWAKENING • ONLINE";
      document.querySelector(".tactical strong").textContent = "1.3°S 30.5°E • CLOAK DISENGAGED";
      document.querySelector(".tactical small").textContent = "CORE ONLINE • PROTECTION READY";
    }
  } catch (error) {
    status.textContent = "LOCAL BRIDGE UNAVAILABLE";
    consoleBox.textContent += "\n> ERROR: activation bridge unavailable";
  }
});
