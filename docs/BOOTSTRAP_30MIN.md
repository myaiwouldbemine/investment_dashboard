# 新環境 30 分鐘上線（Bootstrap + Checklist）

這份文件對應腳本：
- `deploy/scripts/bootstrap_30min.sh`

目標：在新 WSL 環境中，快速完成基礎可運行狀態，並降低遺漏設定風險。

## 1) 一鍵啟動

```bash
cd /home/<your-user>/.openclaw/workspace/investment_dashboard
bash deploy/scripts/bootstrap_30min.sh --with-systemd
```

若你只想先做本機初始化，不裝 systemd：

```bash
bash deploy/scripts/bootstrap_30min.sh
```

## 2) 腳本會做什麼

1. 檢查必要檔案與命令
2. 建立/重用 `.venv`
3. 安裝 `requirements.txt`
4. 啟用 `.githooks`（資料不上 GitHub 防呆）
5. 可選安裝 systemd 服務（API + ngrok）
6. 可選 smoke test（啟 API + ngrok 並驗證 `/health`）

## 3) 30 分鐘 Checklist

- [ ] `python3` / `git` / `curl` 可用
- [ ] `ngrok` 已安裝並設定 authtoken
- [ ] `bootstrap_30min.sh` 成功執行
- [ ] `systemctl status investment-dashboard-api.service --no-pager` 顯示 active（若有安裝）
- [ ] `systemctl status investment-dashboard-ngrok-api.service --no-pager` 顯示 active（若有安裝）
- [ ] `curl -s http://127.0.0.1:8000/health` 回傳 `{"status":"ok"}`
- [ ] `cat /tmp/investment_api_ngrok_url` 有可用 https URL
- [ ] Streamlit Cloud Secret `INVESTMENT_API_BASE_URL` 已更新為最新 ngrok URL
- [ ] 本機 `http://localhost:8501` 可開
- [ ] 雲端 Streamlit 可開且有數字
- [ ] Telegram `/invest` 能正常回覆

## 4) 常見失敗點

1. `ngrok not found`
- 安裝：`sudo snap install ngrok`

2. `/health` 不通
- 先看 API log：`/tmp/investment_api.log`

3. 雲端沒數據
- 常見是 `INVESTMENT_API_BASE_URL` 還是舊 ngrok URL
- 更新 Secret 後 `Reboot app`

4. 誤把資料檔加入 git
- 用：
```bash
git restore --staged data/ "*.parquet" "*.xlsx" "*.xls" "*.csv"
```