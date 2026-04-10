# Operations

Quick commands for the dashboard API, web UI, and Cloudflare Tunnel.

## Check

systemctl status investment-dashboard-api --no-pager
systemctl status investment-dashboard-web --no-pager
systemctl status investment-dashboard-tunnel --no-pager
journalctl -u investment-dashboard-api -n 50 --no-pager
journalctl -u investment-dashboard-web -n 50 --no-pager
journalctl -u investment-dashboard-tunnel -n 50 --no-pager
curl http://127.0.0.1:8000/health
cat /tmp/investment_dashboard_tunnel_url

## Restart

sudo systemctl restart investment-dashboard-api
sudo systemctl restart investment-dashboard-web
sudo systemctl restart investment-dashboard-tunnel

## Install Tunnel Service

sudo cp /home/ericarthuang/.openclaw/workspace/investment_dashboard/deploy/systemd/investment-dashboard-tunnel.service /etc/systemd/system/investment-dashboard-tunnel.service
sudo systemctl daemon-reload
sudo systemctl enable investment-dashboard-tunnel
sudo systemctl restart investment-dashboard-tunnel

## Tunnel URL (No Re-Find)

Tunnel writes latest quick URL here:
/tmp/investment_dashboard_tunnel_url

If file is empty, inspect tunnel logs:
journalctl -u investment-dashboard-tunnel -n 80 --no-pager
tail -n 40 /tmp/cloudflared-tunnel.log

## Quick Check (3 Steps)

1) api, web, tunnel are running
systemctl status investment-dashboard-api --no-pager
systemctl status investment-dashboard-web --no-pager
systemctl status investment-dashboard-tunnel --no-pager

2) api health
curl http://127.0.0.1:8000/health

3) public dashboard URL
cat /tmp/investment_dashboard_tunnel_url
curl -I -L --max-time 20 "$(cat /tmp/investment_dashboard_tunnel_url)"

## Look For

- active (running) in all three services.
- Uvicorn running on http://0.0.0.0:8000 in API journal.
- Streamlit startup messages in web journal.
- tunnel URL line in tunnel journal.
- status=ok from /health.
- HTTP 200 from the tunnel URL.
