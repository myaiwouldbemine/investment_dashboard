# Dashboard Ops Learning Guide

This document is written for learning. It explains how the dashboard stack works, why failures happen, and how to reason about fixes.

## 1) System Model (How things connect)

There are 4 layers:
1. Streamlit UI (`app.py`) on port `8501`
2. API service (`api.py` via uvicorn) on port `8000`
3. Tunnel (`cloudflared`) that maps a public URL to `localhost:8501`
4. Telegram bot (`python -m app.main`) that sends an "Open dashboard" button URL

If any one layer is wrong, user experience breaks in a specific way.

## 2) Failure Patterns and What They Mean

### A) Sidebar first page shows `settings` or homepage appears blank
What it means:
- Streamlit Cloud app entry is set to `config/settings.py` instead of `app.py`.

Why it happens:
- Streamlit uses the selected main file as the first page.
- `settings.py` is primarily a config module, not a page designed for direct user rendering.

How to fix:
- Preferred: set Streamlit Cloud Main file path to `app.py`.
- If you must keep `config/settings.py` as entry, keep this guard:

```python
if __name__ == "__main__":
    import sys as _sys
    _sys.path.insert(0, str(PROJECT_ROOT))
    from app import main as _main
    _main()
```

### B) Telegram `/invest` replies twice
What it means:
- More than one bot process is polling updates.

Why it happens:
- Telegram long-polling is not multi-consumer-safe for the same bot token in this setup.

How to verify:
```bash
pgrep -af "python -m app.main"
```

Fix principle:
- Keep exactly one bot instance.

### C) Telegram button opens 502 Bad Gateway
What it means:
- Public tunnel exists, but cannot reach local Streamlit origin.

Why it happens:
- Streamlit on `8501` is down (or restarted), while tunnel still points to it.

How to verify:
```bash
curl -I http://127.0.0.1:8501
tail -n 80 /tmp/cloudflared-tunnel.log
```

Key log clue:
- `connect: connection refused` to `127.0.0.1:8501`

### D) Telegram message fails with URL error (sendMessage 400)
What it means:
- Button URL is not acceptable by Telegram.

Why it happens:
- `http://localhost:8501` is local-only and invalid for Telegram button links.

Fix principle:
- Use public HTTPS URL for button links.

## 3) URL Strategy (Stable vs Dynamic)

### Stable URL (education-friendly, less surprise)
Use:
- `INVESTMENT_DASHBOARD_URL=https://myai-investment-dashboard.streamlit.app/`

Benefits:
- Link does not change.
- Easier for users and documentation.

Tradeoff:
- You must keep Streamlit Cloud deployment healthy and updated.

### Dynamic tunnel URL (debug-friendly, rapid local testing)
Use:
- `/tmp/investment_dashboard_tunnel_url`

Benefits:
- Fast local validation.

Tradeoff:
- URL rotates; old Telegram buttons can become stale.

## 4) Core Commands (with intent)

### Service health snapshot
```bash
systemctl status investment-dashboard-api --no-pager
systemctl status investment-dashboard-web --no-pager
systemctl status investment-dashboard-tunnel --no-pager
curl http://127.0.0.1:8000/health
curl -I http://127.0.0.1:8501
cat /tmp/investment_dashboard_tunnel_url
```

Learning intent:
- Distinguish "API healthy" from "UI healthy" from "Public URL healthy".

### Logs that teach root cause
```bash
journalctl -u investment-dashboard-api -n 50 --no-pager
journalctl -u investment-dashboard-web -n 50 --no-pager
journalctl -u investment-dashboard-tunnel -n 80 --no-pager
tail -n 80 /tmp/cloudflared-tunnel.log
```

Learning intent:
- Map each symptom to one service layer.

### Restart sequence
```bash
sudo systemctl restart investment-dashboard-api
sudo systemctl restart investment-dashboard-web
sudo systemctl restart investment-dashboard-tunnel
```

Learning intent:
- Recover full path from data source to public entrypoint.

## 5) Deploy Thinking

If cloud still shows old behavior after local fix, think in this order:
1. Is code committed?
2. Is code pushed to `origin/main`?
3. Did Streamlit Cloud redeploy latest commit?
4. Is Main file path pointing to the intended file?

Useful commands:
```bash
git status -sb
git log --oneline -n 5
git pull --rebase origin main
git push origin main
```

## 6) Quick Learning Checklist Before Saying "Fixed"

1. Dashboard homepage renders expected summary cards.
2. Telegram `/invest` returns exactly one reply.
3. "Open dashboard" points to the intended URL mode (stable or dynamic).
4. Public URL opens without blank/502.
5. Process count for bot is exactly one.

When all 5 pass, issue is truly closed.

## 7) Common Pitfalls (Beginner Traps)

1. Mistaking Codespaces for Streamlit Cloud settings
- Symptom: You click a pencil icon and land in `github.dev` / VS Code web.
- Reality: That edits repository files, not Streamlit Cloud app runtime settings.
- Fix: Open [share.streamlit.io](https://share.streamlit.io) and change app settings there.

2. Renaming `settings.py` to `app.py` instead of changing Main file path
- Symptom: People try to rename files to change homepage behavior.
- Reality: Streamlit Cloud homepage comes from **Main file path** setting, not file rename.
- Fix: Keep project structure; set Main file path to `app.py` in Streamlit Cloud.

3. Using `localhost` as Telegram button URL
- Symptom: `/invest` message fails or button is invalid.
- Reality: Telegram clients cannot open your server-local `localhost`.
- Fix: Use public HTTPS URL (Streamlit Cloud URL or valid tunnel URL).

4. Believing old Telegram button should still work after tunnel rotates
- Symptom: Old button opens blank/502 while new one works.
- Reality: `trycloudflare` URLs are temporary and can change.
- Fix: Prefer stable URL mode for production-like usage.

5. Debugging cloud issue with only local status
- Symptom: Local app works, cloud still fails.
- Reality: Local and cloud are separate environments/commits/settings.
- Fix: Verify commit is pushed, cloud redeploy finished, and Main file path is correct.
