# Investment Dashboard

如果你想先看整個 workspace 的正式關聯圖，請先讀 [ARCHITECTURE.md](/home/ericarthuang/.openclaw/workspace/ARCHITECTURE.md:1)。
如果你想先知道文件怎麼讀、該先看哪份，再看 [DOCUMENTS_GUIDE.md](/home/ericarthuang/.openclaw/workspace/DOCUMENTS_GUIDE.md:1)。

這個專案可以先理解成兩層：

- `API`：提供投資摘要與圖表資料
- `Streamlit UI`：把資料整理成 dashboard 畫面

這個專案是投資管理 Dashboard（Streamlit），模組包含：

- Bonds
- Stocks
- FCN

Telegram 可透過 `/invest` 系列查摘要，並附上 `Open dashboard` 按鈕。

這裡的 Telegram 指的是獨立的 `telegram-ai-assistant` bot，
不是 OpenClaw gateway 裡的一般聊天 channel。

## GitHub 與資料保密原則

本 repo **只放程式碼與設定，不放任何資料檔**。

- `data/` 全目錄不進 Git
- `*.parquet`, `*.xlsx`, `*.xls`, `*.csv` 不進 Git
- 已提供 pre-commit 防呆（可阻擋誤提交資料檔）

一次性啟用防呆：

```bash
git config core.hooksPath .githooks
```

## 建議保留在 GitHub 的內容

```text
investment_dashboard/
  app.py
  api.py
  requirements.txt
  .gitignore
  .githooks/
  .streamlit/
    config.toml
  config/
  docs/
  pages/
  src/
  tests/
  deploy/
```

## 本機啟動

```bash
streamlit run app.py --server.port 8501
```

如果你是第一次接手這條系統，建議用這個順序理解：

1. 先看 `README_操作說明.md`，理解使用者怎麼操作
2. 再看 `api.py`，理解 dashboard 依賴哪些資料接口
3. 最後看 `docs/STREAMLIT_COMMUNITY_CLOUD.md`，理解部署方式

## 部署到 Streamlit Community Cloud

1. 把程式碼推到 GitHub（不要含資料檔）
2. 到 Streamlit Community Cloud 建立 app
3. Main file path 填 `app.py`
4. Python 建議 `3.12`

詳細步驟：`docs/STREAMLIT_COMMUNITY_CLOUD.md`
