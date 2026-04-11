#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STATE_FILE = PROJECT_ROOT / "data" / "state" / "monitor_state.json"
ENV_FILE = PROJECT_ROOT / ".env"
API_HEALTH_URL = "http://127.0.0.1:8000/health"
NGROK_TUNNELS_URL = "http://127.0.0.1:4040/api/tunnels"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fetch_json(url: str, timeout: float = 5.0) -> dict[str, object]:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "investment-dashboard-monitor/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check_api_health() -> tuple[bool, str]:
    try:
        payload = fetch_json(API_HEALTH_URL)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return False, f"health endpoint unavailable: {exc}"
    status = str(payload.get("status", "")).strip().lower()
    if status != "ok":
        return False, f"unexpected health payload: {payload}"
    return True, "ok"


def get_ngrok_public_url() -> tuple[str | None, str]:
    try:
        payload = fetch_json(NGROK_TUNNELS_URL)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        return None, f"ngrok API unavailable: {exc}"

    tunnels = payload.get("tunnels", [])
    if not isinstance(tunnels, list):
        return None, "ngrok API returned invalid tunnel payload"

    for tunnel in tunnels:
        if not isinstance(tunnel, dict):
            continue
        public_url = str(tunnel.get("public_url", "")).strip()
        if public_url.startswith("https://"):
            return public_url, "ok"
    return None, "no https ngrok tunnel found"



def send_telegram_alert(message: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_ALERT_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("missing TELEGRAM_BOT_TOKEN or TELEGRAM_ALERT_CHAT_ID")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = urlencode(
        {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")

    req = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(req, timeout=10) as resp:
        if resp.status != 200:
            raise RuntimeError(f"telegram send failed: HTTP {resp.status}")


def build_alerts(previous_state: dict[str, object], api_ok: bool, api_reason: str, ngrok_url: str | None, ngrok_reason: str) -> tuple[list[str], bool]:
    alerts: list[str] = []
    has_failure = False

    previous_api_ok = previous_state.get("api_ok")
    previous_ngrok_url = str(previous_state.get("ngrok_url", "")).strip() or None

    if not api_ok:
        has_failure = True
        if previous_api_ok is not False:
            alerts.append(f"[Investment Dashboard] API health check failed: {api_reason}")

    if ngrok_url is None:
        has_failure = True
        if previous_ngrok_url is not None:
            alerts.append(f"[Investment Dashboard] ngrok tunnel unavailable: {ngrok_reason}")
    elif previous_ngrok_url and previous_ngrok_url != ngrok_url:
        alerts.append(
            "[Investment Dashboard] ngrok URL changed:\n"
            f"old: {previous_ngrok_url}\n"
            f"new: {ngrok_url}"
        )

    return alerts, has_failure


def main() -> int:
    load_dotenv(ENV_FILE)
    previous_state = load_state(STATE_FILE)

    api_ok, api_reason = check_api_health()
    ngrok_url, ngrok_reason = get_ngrok_public_url()
    alerts, has_failure = build_alerts(previous_state, api_ok, api_reason, ngrok_url, ngrok_reason)

    sent_alerts: list[str] = []

    for message in alerts:
        try:
            send_telegram_alert(message)
        except Exception as exc:
            print(f"[warn] telegram alert failed: {exc}")

    state = {
        "api_ok": api_ok,
        "api_reason": api_reason,
        "checked_at": utc_now_iso(),
        "last_alerts": sent_alerts,
        "ngrok_reason": ngrok_reason,
        "ngrok_url": ngrok_url,
    }
    save_state(STATE_FILE, state)
    return 1 if has_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
