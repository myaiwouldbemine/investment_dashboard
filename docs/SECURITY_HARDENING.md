# Security Hardening

## Canonical Secrets

Use only these environment variable names across local `.env`, Streamlit secrets, and operational runbooks:

- `INVESTMENT_API_BASE_URL`
- `DASHBOARD_LINK_SECRET`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_ALERT_CHAT_ID`

Deprecated aliases should be removed during the next maintenance window instead of being carried forward indefinitely.

## Token Rotation SOP

1. Create the replacement credential first.
2. Update the secret in the authoritative store:
   - local runtime: `.env`
   - Streamlit Cloud: `.streamlit/secrets.toml` or platform secret UI
   - Telegram bot operator notes if a manual fallback exists
3. Restart the affected process after the new value is in place:
   - API / monitor timer on the WSL host
   - Streamlit app if `INVESTMENT_API_BASE_URL` or `DASHBOARD_LINK_SECRET` changed
4. Validate the new credential immediately:
   - `curl -s http://127.0.0.1:8000/health`
   - `python deploy/scripts/health_monitor.py`
   - signed dashboard link access from Telegram
5. Revoke the old credential after validation succeeds.
6. Record the rotation date, owner, and impacted systems.

## Least Privilege Checklist

- `TELEGRAM_BOT_TOKEN` should belong to a bot used only for this dashboard workflow.
- `TELEGRAM_ALERT_CHAT_ID` should point to the narrowest operational chat that still reaches responders.
- `DASHBOARD_LINK_SECRET` should be shared only between the Telegram link generator and Streamlit access gate.
- `.env` and `.streamlit/secrets.toml` must stay out of git and out of screenshots/shared logs.
- systemd services should run as the dedicated user account already used by the dashboard host, not as `root`.
- ngrok should expose only the required API port, not the full app workspace.

## Secret Exposure Response

1. Assume the exposed value is compromised immediately.
2. Rotate the leaked credential and deploy the replacement before any forensic cleanup.
3. Invalidate dependent access paths:
   - regenerate `DASHBOARD_LINK_SECRET` to break existing signed links
   - revoke and recreate the Telegram bot token if it leaked
   - replace the externally shared `INVESTMENT_API_BASE_URL` if the old endpoint should no longer be trusted
4. Review logs for suspicious use after the estimated exposure time.
5. Notify affected operators with the exact compromised secret name, exposure window, and remediation completion time.
6. Capture follow-up actions if the leak source was process-related, for example shell history, copied screenshots, or accidental commits.
