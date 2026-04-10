# Streamlit Community Cloud 部署教學

這份教學是給目前這個專案使用的。

## 先準備什麼

在開始之前，先確認三件事：

1. 你已經有 GitHub 帳號
2. 這個專案內容已經推上 GitHub
3. `app.py` 可以在本機正常執行

## 第一步：把專案推上 GitHub

如果目前還不是 git repo，可以在 WSL 專案目錄執行：

```bash
git init
git add .
git commit -m "Prepare dashboard for GitHub and Streamlit Cloud"
```

接著建立 GitHub repo，再把它 push 上去。

## 第二步：進 Streamlit Community Cloud

到 [Streamlit Community Cloud](https://share.streamlit.io/) 後：

1. 登入帳號
2. 連接 GitHub
3. 點右上角 `Create app`

官方說明：
- [Deploy your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [File organization](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization)

## 第三步：填部署資訊

建立 app 時，主要填這些：

- Repository: 你的 GitHub repo
- Branch: `main` 或你實際使用的 branch
- Main file path: `app.py`

如果要用固定好記的網址，也可以在建立時自訂 subdomain。

## 第四步：Advanced settings

Community Cloud 現在建議使用仍在支援中的 Python 版本。這個專案建議選 `Python 3.12`。

如果之後有需要環境變數或 secrets，可以在這裡補。

官方說明：
- [Deploy your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [App settings](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings)

## 第五步：部署完成後要做什麼

部署完成後，你會拿到一個固定網址，例如：

```text
https://your-dashboard-name.streamlit.app
```

這時候建議馬上做兩件事：

1. 打開網站，確認首頁和三個分頁都正常
2. 把 Telegram bot 的 `INVESTMENT_DASHBOARD_URL` 改成這條固定網址

這樣 Telegram 裡的 `Open dashboard` 按鈕就不需要再依賴會變動的 quick tunnel。

## 如果之後更新畫面

之後只要：

1. 改程式
2. push 到 GitHub

Streamlit Community Cloud 就會自動重新部署。

官方說明：
- [Manage your app](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app)

## 建議你第一次部署時這樣做

最順的順序是：

1. 先把這個 repo 推上 GitHub
2. 先完成一次 Streamlit Community Cloud 部署
3. 先確認網址固定可開
4. 再回頭改 Telegram 的 dashboard 按鈕

這樣可以避免一邊改 bot，一邊又遇到網址還沒固定的問題。
