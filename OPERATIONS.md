# Dashboard Ops Learning Guide (Latest)

這份文件是教學版操作手冊，目標是讓你知道「怎麼做」與「為什麼這樣做」。

## 1) 最新系統架構

目前實際路徑是：
1. Telegram 指令 -> 回摘要文字
2. 按鈕開啟 Streamlit Cloud Dashboard
3. Streamlit Cloud 透過 `INVESTMENT_API_BASE_URL` 呼叫你本機 API（經 ngrok）
4. API 回摘要與圖表資料 JSON

重點：
- 資料檔留在本機，不放 GitHub
- GitHub 只放程式碼與文件

## 2) 為何會出現「首頁有數字但圖表不見」

通常是兩種原因：
1. API 只有摘要 endpoint 可用，chart endpoint 失敗
2. `INVESTMENT_API_BASE_URL` 指到舊的 ngrok URL

所以要分層檢查：
- `/health`
- `/api/v1/investments/*`
- `/api/v1/investments/charts/*`

## 3) 正確更新資料流程

請以 `setup.md` 為主；核心是：

```bash
bash deploy/scripts/update_data_files.sh --run-pipeline
```

然後驗證：
- 本機 Streamlit
- API chart endpoints
- 雲端 Streamlit
- Telegram `/invest`

## 4) GitHub 保密策略（必遵守）

1. `.gitignore` 已封鎖：
- `data/`
- `*.parquet`
- `*.xlsx`, `*.xls`, `*.csv`

2. pre-commit hook 已封鎖資料提交。

3. 推送前固定做：

```bash
git add -A
git restore --staged data/ "*.parquet" "*.xlsx" "*.xls" "*.csv" || true
git status --short
```

## 5) 開機自動啟動（WSL）

目前使用 systemd 服務：
- `investment-dashboard-api.service`
- `investment-dashboard-ngrok-api.service`

檢查：

```bash
systemctl status investment-dashboard-api.service --no-pager
systemctl status investment-dashboard-ngrok-api.service --no-pager
```

## 6) 發布與回歸檢查清單

每次改程式後至少檢查：
1. settings 首頁摘要是否正常
2. Bonds/Stocks/FCN 三頁都能開
3. 三頁圖表是否顯示
4. `/invest` 回覆是否正常
5. Open dashboard 連結可開

## 7) 一次性安全設定

```bash
git config core.hooksPath .githooks
```

如果你換了新機或新 clone，請再執行一次。

## 8) Code-Doc Mapping (How It Actually Runs)

1. Data-source fallback (UI): `app.py`
   - API first, then per-section parquet fallback.
2. Query router (API): `src/services/investment_summary_service.py::query_summary`
   - Alias matching + detail keyword dispatch.
3. Chart aggregation (API): `build_*_charts_payload`
   - Groupby/pivot/weight normalization, then JSON-native conversion.
4. JSON safety layer: `_to_native` + `_safe_records`
   - Prevent numpy scalar serialization errors.
