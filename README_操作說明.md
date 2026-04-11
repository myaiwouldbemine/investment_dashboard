# 投資管理儀表板 使用教學

這份說明主要是帶你快速上手目前這套 `Dashboard + Telegram Bot`。

你可以把它理解成兩個入口：
- `Dashboard`：適合看圖表、結構分析、明細查詢
- `Telegram`：適合先快速看摘要，再決定要不要點進 dashboard

目前系統主要看三個模組：
- `Bonds`
- `Stocks`
- `FCN`

`Deposit` 目前先不使用，所以首頁與 Telegram 總覽都不會再放進來。

---

## 先從哪裡開始
如果你只是想先快速確認今天的投資狀況，最簡單的做法是：

1. 先在 Telegram 輸入 `/invest`
2. 看 `債券摘要 / 股票摘要 / FCN 摘要`
3. 如果要進一步看圖表或明細，再按 `Open dashboard`

如果你已經知道自己要看哪一個模組，也可以直接進 dashboard 左側分頁。

---

## Dashboard 怎麼看

### 進入方式
你可以用兩種方式打開：
- 在 Telegram 點 `Open dashboard`
- 直接開啟目前部署的 dashboard 網址

### 首頁可以做什麼
首頁的作用是先快速導到你要的模組。

你會看到三張入口卡：
- `Bonds`
- `Stocks`
- `FCN`

下面還有三塊摘要卡，讓你不用切頁就能先看核心數字。

### 左側分頁
目前左側分頁會看到：
- `Bond Portfolio`
- `Stock Portfolio`
- `FCN Portfolio`

如果你找不到 `Deposit Portfolio`，那是正常的，因為這個模組目前先停用。

---

## Bonds 要怎麼看
`Bond Portfolio` 適合看債券整體配置與部位查詢。

你可以先看上方的整體概況，主要指標是：
- 投資金額
- 平均收益率
- 平均存續年數

再往下看：
- 結構分析
- 債券明細查詢

如果你只是想知道目前債券整體狀況，先看整體概況就夠。
如果你要找特定交易對象或部位，再往下看明細表。

---

## Stocks 要怎麼看
`Stock Portfolio` 適合看股票目前是賺還是賠，以及持倉集中在哪裡。

先看上方四個數字：
- 投資金額
- 市值
- 未實現損益
- 整體報酬率

再往下看幾個重點區塊：
- 公司別損益分析
- 個股損益分析
- 個股市值分析
- 股票明細查詢

如果你想知道哪一檔表現最好或最差，可以直接看個股損益分析。
如果你想知道目前持倉集中在哪些股票，可以看個股市值分析。

---

## FCN 要怎麼看
`FCN Portfolio` 主要是看 FCN 的投資金額、利息，以及未到期部位。

先看上方的摘要數字：
- 總投資額
- 總利息
- 未到期金額
- 未到期利息

再往下看：
- 各公司投資金額（已到期 vs 未到期）
- 投資金額佔比
- `FCN Analysis 1`
- `FCN Analysis 2`
- `未到期 FCN 明細查詢`

如果你現在最在意的是還沒到期的 FCN，就直接看：
- 未到期金額
- 未到期利息
- 未到期 FCN 明細查詢

---

## Telegram 怎麼查
Telegram 比較適合先看摘要，不一定每次都要打開 dashboard。

### 看整體總覽
你可以輸入：
- `/invest`
- `/invest overview`
- `/投資總覽`

這會回你三段摘要：
- 債券摘要
- 股票摘要
- FCN 摘要

### 看單一模組
如果只想看其中一個模組，可以直接輸入：

#### 債券
- `/invest bonds`
- `/債券`
- `/bonds`

#### 股票
- `/invest stocks`
- `/股票`
- `/stocks`

#### FCN
- `/invest fcn`
- `/fcn`
- `/FCN`

### 查特定標的或條件
如果你想查更細的內容，可以把關鍵字接在指令後面：
- `/股票 日本菸草`
- `/債券 Morgan Stanley`
- `/fcn COMBO`

這種查法適合用來快速確認單一標的或單一條件。

---

## Telegram 回覆會看到什麼

### `/invest bonds`
通常會看到：
- 投資金額
- 平均收益率
- 平均存續年數

### `/invest stocks`
通常會看到：
- 投資金額
- 市值
- 未實現損益
- 整體報酬率

### `/invest fcn`
通常會看到：
- 總投資額
- 總利息
- 未到期金額
- 未到期利息

每次查詢後，底下通常都會有 `Open dashboard` 按鈕。
如果你覺得摘要還不夠，再點進 dashboard 看圖表和明細就可以。

---

## 目前資料來源
目前各模組使用的來源檔如下：

### Bonds
- `Bonds Analysis.xlsx`

### Stocks
- 簡化版 `Stocks.xlsx`

### FCN
- `FCNs_20260409.xlsx`

如果之後資料檔更新，通常只要重新跑 pipeline，dashboard 和 Telegram 摘要就會跟著更新。

---

## 一個最常用的操作方式
如果你只是日常查看，我會建議這樣用：

1. 先在 Telegram 輸入 `/invest`
2. 看哪一個模組今天最需要注意
3. 如果要看細節，就按 `Open dashboard`
4. 進 dashboard 後再切到 `Bond / Stock / FCN` 分頁
5. 如果要查單一標的，再回 Telegram 用細查指令

這樣通常是最快的。

---

## 如果遇到問題

### Telegram 回兩次
通常代表 bot 在背景跑了兩個程序。
這種情況只要把 bot 清成單一程序即可。

### 手機有收到、桌機沒看到
通常是 Telegram Desktop 沒即時刷新。
重新整理、切換對話，或重開桌機版通常就會好。

### Dashboard 打不開
先確認 `Open dashboard` 按鈕對應的網址是否仍有效。
如果是 tunnel 或臨時網址，也要注意是否已變更。

---

## 接下來還可以怎麼擴充
如果之後你還想繼續往前做，這幾個方向最有價值：
- 加更自然語言的查詢，例如：`查 FCN COMBO`
- 做每天固定時間的摘要推送
- 補更細的 drill-down 分析
- 加例外提醒或異常摘要
---

## 第一次使用建議順序
如果是第一次開始用這套系統，可以先照這個順序走一次，通常會最快進入狀況：

1. 先在 Telegram 輸入 `/invest`
   先看目前整體是債券、股票還是 FCN 比較需要注意。

2. 挑一個你最想看的模組再查一次
   例如：
   - `/invest bonds`
   - `/invest stocks`
   - `/invest fcn`

3. 如果摘要看起來需要進一步確認，再按 `Open dashboard`
   進 dashboard 後切到對應分頁看圖表和明細。

4. 如果你已經知道要查哪個標的，直接用細查指令
   例如：
   - `/股票 日本菸草`
   - `/債券 Morgan Stanley`
   - `/fcn COMBO`

5. 最後再回到 dashboard 看完整結構
   Telegram 比較適合先看摘要；要看整體配置、圖表變化與明細，還是 dashboard 最完整。

如果只是日常快速檢查，通常做到第 1 步和第 2 步就已經很夠用。
---

## 保密與每日操作（最新版）

### A. 資料保密原則
- 資料檔（Excel/Parquet/CSV）留在本機，不上 GitHub。
- GitHub 只放程式碼、設定與文件。

### B. 每日更新最短路徑

```bash
cd /home/ericarthuang/.openclaw/workspace/investment_dashboard
bash deploy/scripts/update_data_files.sh --run-pipeline
```

更新後驗證：
1. 本機 `http://localhost:8501`
2. API `curl -s http://127.0.0.1:8000/health`
3. Telegram `/invest`

### C. 何時才需要 git push
只有在你改「程式/設定/文件」時才 push，且要排除資料檔：

```bash
git add -A
git restore --staged data/ "*.parquet" "*.xlsx" "*.xls" "*.csv" || true
git status --short
git commit -m "update code/docs"
git pull --rebase origin main
git push origin main
```