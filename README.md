# Investment Dashboard

這個專案是投資管理 Dashboard（Streamlit），模組包含：

- Bonds
- Stocks
- FCN

Telegram 可透過 `/invest` 系列查摘要，並附上 `Open dashboard` 按鈕。

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

## 部署到 Streamlit Community Cloud

1. 把程式碼推到 GitHub（不要含資料檔）
2. 到 Streamlit Community Cloud 建立 app
3. Main file path 填 `app.py`
4. Python 建議 `3.12`

詳細步驟：`docs/STREAMLIT_COMMUNITY_CLOUD.md`
