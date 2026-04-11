# API + ngrok 自動啟動與資料更新（教育版）

這份是實戰版操作說明，聚焦兩件事：
1. API + ngrok 穩定運行
2. 資料更新後可被雲端正確讀到

## A) 手動啟停（排錯優先）

啟動：

```bash
cd /home/ericarthuang/.openclaw/workspace/investment_dashboard
./deploy/scripts/start_api_ngrok_stack.sh
```

停止：

```bash
./deploy/scripts/stop_api_ngrok_stack.sh
```

你會拿到：
- API 在 `localhost:8000`
- ngrok 公網 URL（寫入 `/tmp/investment_api_ngrok_url`）

## B) 開機自動啟動（正式使用）

安裝服務（一次性）：

```bash
cd /home/ericarthuang/.openclaw/workspace/investment_dashboard
sudo cp deploy/systemd/investment-dashboard-api.service /etc/systemd/system/
sudo cp deploy/systemd/investment-dashboard-ngrok-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now investment-dashboard-api.service
sudo systemctl enable --now investment-dashboard-ngrok-api.service
```

狀態確認：

```bash
systemctl status investment-dashboard-api.service --no-pager
systemctl status investment-dashboard-ngrok-api.service --no-pager
```

## C) Streamlit Cloud Secret 設定

`INVESTMENT_API_BASE_URL` 要填「ngrok 的 https URL（不加結尾 /）」。

範例：

```text
INVESTMENT_API_BASE_URL="https://xxxx-xxxx.ngrok-free.dev"
```

更換 ngrok URL 後，請更新 Secret 並 Reboot app。

## D) 資料更新

```bash
cd /home/ericarthuang/.openclaw/workspace/investment_dashboard
./deploy/scripts/update_data_files.sh --run-pipeline
```

預設來源：
- `/mnt/c/Users/ericarthuang/Downloads`

固定檔名：
- `bond_source.xlsx`
- `stock_source.xlsx`
- `fcn_source.xlsx`

## E) 驗證順序（非常重要）

1. API 健康：
```bash
curl -s http://127.0.0.1:8000/health
```

2. 摘要 endpoint：
```bash
curl -s http://127.0.0.1:8000/api/v1/investments/bonds | head
curl -s http://127.0.0.1:8000/api/v1/investments/stocks | head
curl -s http://127.0.0.1:8000/api/v1/investments/fcn | head
```

3. 圖表 endpoint：
```bash
curl -s http://127.0.0.1:8000/api/v1/investments/charts/bonds | head
curl -s http://127.0.0.1:8000/api/v1/investments/charts/stocks | head
curl -s http://127.0.0.1:8000/api/v1/investments/charts/fcn | head
```

只要 chart JSON 回傳 `"available": true`，雲端圖表通常就能畫出來。