# Local health monitor for the stdlib license server.
# Configure HEALTH_URL (default port 8787), TELEGRAM_BOT_TOKEN, and TELEGRAM_CHAT_ID.
import json
import os
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")
if os.path.exists(ENV_FILE):
    with open(ENV_FILE, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = os.environ.get("HEALTH_URL", "http://127.0.0.1:8787/health")
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
LOG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "health-monitor.log")
os.makedirs(os.path.dirname(LOG), exist_ok=True)


def notify(message):
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(f"{stamp} {message}\n")
    if not TOKEN or not CHAT_ID:
        return
    body = json.dumps({"chat_id": CHAT_ID, "text": f"XTOBE License Server\n{message}"}).encode()
    req = Request(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data=body,
                  headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=15) as response:
            response.read()
    except Exception as exc:
        with open(LOG, "a", encoding="utf-8") as handle:
            handle.write(f"{stamp} Telegram delivery failed: {exc}\n")


def check():
    try:
        with urlopen(Request(URL, headers={"User-Agent": "XTOBE-health-monitor"}), timeout=10) as response:
            data = json.loads(response.read().decode())
            if response.status == 200 and data.get("ok"):
                return "OK uptime={}s licenses={}".format(data.get("uptime_seconds", "?"), data.get("license_count", "?"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        return "FAIL {}".format(exc)
    return "FAIL health response was not healthy"


failures = 0
was_down = False
while True:
    result = check()
    if result.startswith("OK"):
        if was_down:
            notify("RECOVERED - {}".format(result))
        else:
            notify(result)
        failures = 0
        was_down = False
    else:
        failures += 1
        if failures >= 3 and not was_down:
            notify("DOWN after 3 failed checks - {}".format(result))
            was_down = True
    time.sleep(60)
