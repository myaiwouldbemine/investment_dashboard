# Streamlit Community Cloud 部署教學（最新版）

## 1) 部署前原則

- GitHub 僅存程式碼與文件
- 資料檔不上 GitHub（data/parquet/xlsx/csv）
- Dashboard 主檔固定 `app.py`

## 2) 第一次推版

```bash
cd /home/ericarthuang/.openclaw/workspace/investment_dashboard
git init
git add -A
git restore --staged data/ "*.parquet" "*.xlsx" "*.xls" "*.csv" || true
git commit -m "prepare streamlit cloud deployment"
```

然後建立 GitHub repo，push 到 `main`。

## 3) 在 Streamlit Cloud 建 app

- Repository: 你的 repo
- Branch: `main`
- Main file path: `app.py`
- Python: 建議 `3.12`

## 4) Secrets（關鍵）

至少要確認：

```text
INVESTMENT_API_BASE_URL="https://<your-ngrok-domain>"
DASHBOARD_LINK_SECRET="<same-secret-as-telegram-side>"
```

如果使用 Telegram 白名單驗證，也要確認對應 secret 與程式端一致。

## 5) 每次更新後怎麼驗證

1. Streamlit Cloud 首頁是否可開
2. Bonds/Stocks/FCN 三頁是否有圖表
3. Telegram `/invest` 數字是否一致
4. 若異常先 Reboot app

## 6) 一次性啟用提交防呆

```bash
git config core.hooksPath .githooks
```

這會在你 commit 前阻擋資料檔誤提交。