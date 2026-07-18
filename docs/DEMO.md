# Englex 功能 Demo

以下是本機實際執行的 CLI 輸出。命令只使用本機 Englex 與本機詞庫；wishlist 段落以一次性 `XDG_DATA_HOME` 執行，沒有把個人資料寫入 repo 或預設資料目錄。

## 1. 上下文消歧

命令：

```bash
englex scan "roll out canary to 5% traffic"
```

實際輸出：

```text
範圍：9:15；命中：canary；類型：canonical
canary
狀態：常用
信任等級：legacy（既有隨附，未回溯驗證）
別名：—
來源紀錄：legacy；未追溯驗證
資料層：curated
最可能義項：2（命中線索：traffic）
可能義項：
1. [發布／SRE] 早期或實驗性發布通道；在版本名稱與套件標籤中通常保留 canary。
   線索：channel, nightly, package tag
2. 最可能；[發布／SRE] 以少量流量或使用者驗證新版本的 canary deployment。
   線索：traffic, rollout, deployment
3. [測試／SRE] 用於及早偵測問題的 canary test 或監測檢查。
   線索：test, monitor, health check
注意：需要上下文；請依所在產品、團隊或技術文件確認。

未命中：roll, out, to, 5, traffic

明示新增 private：englex private add --term roll; englex private add --term out; englex private add --term to; englex private add --term 5; englex private add --term traffic
```

這裡 `traffic` 線索使 `canary` 的第 2 義項成為最可能義項；其他義項仍完整保留。

## 2. 信任等級

命令：

```bash
englex lookup daemon
```

實際輸出：

```text
daemon
狀態：常用
信任等級：ai_drafted（AI 草擬，未經人工審定）
別名：—
來源紀錄：no_public_source；來源紀錄，不等同正確性
領域：作業系統／運維
釋義：在背景長時間常駐、通常不附著互動終端的服務行程，用來持續提供系統功能或處理工作。
```

這個結果明確標出 `ai_drafted`，不把草擬內容冒充人工審定。

## 3. Wishlist 迴圈

命令：

```bash
englex wishlist add "some term"
englex wishlist list
```

實際輸出：

```text
已加入本機 wishlist。
some term
```

本次 demo 使用 disposable `XDG_DATA_HOME`；wishlist 是使用者明示開啟的本機資料，不是查詢歷史。

## 4. VS Code 擴充畫面

TODO：**JY 手動錄製** GIF／影片。

需要在 VS Code Extension Development Host 中手動示範：

1. 終端機輸出含 `canary` 或其他已知術語。
2. hover 連結顯示定義與信任等級。
3. 點擊連結後，**Englex Selection** output channel 顯示完整解釋。

本次環境沒有 `asciinema`，因此沒有附 CLI cast，也沒有假裝產生 VS Code 錄影。
