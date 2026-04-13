# Dashboard Ops Learning Guide

這份文件是 `investment_dashboard` 的教學式操作手冊。

如果你是第一次接手這條系統，可以先把它理解成：

- 本機有 `investment_dashboard API`
- 前端是 `Streamlit`
- Telegram bot 會先回摘要，再導向 dashboard
- 如果前端在雲端，會透過 tunnel / ngrok 回打本機 API

如果你想先看正式總圖，請先讀 [ARCHITECTURE.md](/home/ericarthuang/.openclaw/workspace/ARCHITECTURE.md:1)。

## 1. 先理解這條服務實際怎麼跑

目前常見的實際路徑是：

1. Telegram 指令先回摘要文字
2. 使用者按下 `Open dashboard`
3. Streamlit UI 透過 `INVESTMENT_API_BASE_URL` 呼叫本機 API
4. API 回傳摘要與圖表 JSON

這條路徑的重點是：

- 資料檔留在本機
- GitHub 只放程式碼與文件
- dashboard 能不能正常顯示，常常取決於 API 與 tunnel 是否同步正常

## 2. 最常見的問題是什麼

最常見的錯誤通常是：

### A. 首頁有數字，但圖表不見

常見原因：

1. API 摘要 endpoint 正常，但 chart endpoint 失敗
2. `INVESTMENT_API_BASE_URL` 指到舊的 ngrok URL

因此排查時要分層看：

- `/health`
- `/api/v1/investments/*`
- `/api/v1/investments/charts/*`

## 3. 正確更新資料流程

資料更新時，請以 `setup.md` 為主。

最核心的更新指令是：

```bash
bash deploy/scripts/update_data_files.sh --run-pipeline
```

更新後，建議依序驗證：

- 本機 Streamlit
- API chart endpoints
- 雲端 Streamlit
- Telegram `/invest`

## 4. GitHub 保密策略

這一條很重要，而且需要每次都遵守。

目前原則是：

1. `.gitignore` 已封鎖：
   - `data/`
   - `*.parquet`
   - `*.xlsx`
   - `*.xls`
   - `*.csv`
2. pre-commit hook 已封鎖資料提交
3. 推送前仍要再手動檢查一次 staged 狀態

建議固定執行：

```bash
git add -A
git restore --staged data/ "*.parquet" "*.xlsx" "*.xls" "*.csv" || true
git status --short
```

這樣做的教育意義是：

- 先把資料與程式碼分開
- 再把部署與保密邊界講清楚
- 降低把本機資料誤推上 GitHub 的風險

## 5. WSL 開機自動啟動

目前主要使用的 `systemd` 服務是：

- `investment-dashboard-api.service`
- `investment-dashboard-ngrok-api.service`

檢查方式：

```bash
systemctl status investment-dashboard-api.service --no-pager
systemctl status investment-dashboard-ngrok-api.service --no-pager
```

如果你後面也有跑 web 或 monitor 相關服務，請再搭配對應 service 一起看。

## 6. 每次改完程式後，至少做哪些檢查

建議最少檢查這 5 件事：

1. 首頁摘要是否正常
2. `Bonds / Stocks / FCN` 三頁都能開
3. 三頁圖表是否都有顯示
4. Telegram `/invest` 回覆是否正常
5. `Open dashboard` 連結是否打得開

如果這 5 件事都正常，通常代表：

- API 沒壞
- Streamlit 沒壞
- Telegram bot 導流也沒壞

## 7. 一次性安全設定

如果你換了新機器或重新 clone，記得再做一次：

```bash
git config core.hooksPath .githooks
```

這一步的作用是啟用 repo 內建的防呆 hook，避免資料檔被誤提交。

## 8. Code-Doc Mapping

如果你想從程式角度理解文件裡講的流程，可以先對照這幾個點：

1. UI 資料 fallback：`app.py`
   - 先走 API，再 fallback 到本機 parquet
2. API query router：`src/services/investment_summary_service.py::query_summary`
   - 負責 alias matching 與 detail keyword dispatch
3. Chart aggregation：`build_*_charts_payload`
   - 負責 groupby、pivot、weight normalization 與 JSON 轉換
4. JSON safety layer：`_to_native` 與 `_safe_records`
   - 避免 numpy scalar serialization error

## 9. 第一次接手時建議怎麼讀

如果你是第一次接手這條服務，建議這樣看：

1. 先看 `README.md`
2. 再看 `README_操作說明.md`
3. 再看這份 `OPERATIONS.md`
4. 最後看 `api.py`、`app.py`、`setup.md`
