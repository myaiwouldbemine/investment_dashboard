# Investment Dashboard

這個專案是目前正在使用的投資管理 Dashboard，主畫面由 Streamlit 提供，內容分成三個模組：

- Bonds
- Stocks
- FCN

目前 Telegram 已經可以透過 `/invest` 系列指令查詢摘要，並附上 `Open dashboard` 按鈕開啟網頁版。

## 目前這個 repo 是否適合上 GitHub

可以，整理後已經符合上 GitHub 與部署到 Streamlit Community Cloud 的基本條件：

- 入口檔固定為 `app.py`
- 分頁都放在 `pages/`
- 依賴已集中在 `requirements.txt`
- Dashboard 顯示用資料已整理在 `data/processed/**/latest.parquet`
- `.gitignore` 已排除 `.venv`、`data/raw`、歷史 batch 檔與本機雜訊

也就是說，這個版本可以直接當成 GitHub repo 的內容來源。

## GitHub 上建議保留的結構

```text
investment_dashboard/
  app.py
  requirements.txt
  .gitignore
  .streamlit/
    config.toml
  config/
  data/
    processed/
  docs/
  pages/
  src/
  tests/
```

## 本機啟動

```bash
streamlit run app.py --server.port 8501
```

## 要部署到 Streamlit Community Cloud 時

部署重點其實很簡單：

1. 把這個資料夾推到 GitHub
2. 到 Streamlit Community Cloud 建立 app
3. 選擇 repo、branch、entrypoint file
4. entrypoint file 填 `app.py`
5. Python 版本建議選 `3.12`

更詳細的步驟可看：[docs/STREAMLIT_COMMUNITY_CLOUD.md](docs/STREAMLIT_COMMUNITY_CLOUD.md)

## 和 Telegram 的關係

Telegram bot 目前是另外一個專案，但它會讀這個 dashboard 的摘要資料，並把使用者導向 dashboard 網址。

所以實際上：

- Dashboard repo 負責畫面與摘要資料
- Telegram bot 負責指令與按鈕

當 Streamlit Community Cloud 部署完成後，只要把 bot 的 `INVESTMENT_DASHBOARD_URL` 改成新的固定網址即可。
