# englex 產品功能地圖 v0.6

本文件是後續產品開發單元的範圍判斷依據；未列為本層項目的需求，不得藉由小型修正擴張進入產品。

## 一句話定位

englex 是供 WSL 與 VS Code Integrated Terminal 使用的本機、離線優先工程術語查詢工具。核心情境是使用者閱讀 AI／軟體工程英文時，快速查詢單詞或短術語的繁體中文工程語意；它不是全文翻譯器、瀏覽器工具或通用聊天 AI。

## 使用者與環境邊界

- 主要環境：WSL 終端機與 VS Code Integrated Terminal。
- 排除：網頁右鍵翻譯、桌面 Codex 對話介面、任何網站注入與剪貼簿監控。
- 排除原因：前述環境已有更合適的工具，加入它們會擴大隱私暴露面、權限需求與維護範圍，且偏離終端機術語查詢的核心。

## 功能地圖

### 現在的 MVP

| 項目 | 使用者價值 | 輸入與輸出 | 本機資料讀寫 | 隱私／安全限制 | 人工審核 | 最小驗收條件 |
| --- | --- | --- | --- | --- | --- | --- |
| 單詞與短術語 lookup | 快速理解工程語意 | 1–5 詞查詢 → 終端卡片或 JSON | 讀 shipped seed 與 overlay；查詢不寫入 | 無網路、無歷史、不可掃描專案檔案 | 不需要 | 已知 term 回傳 0；未知 term 回傳 1 |
| 多義項與 context-required | 不把不確定語意偽裝成單一翻譯 | term → 全部 sense、脈絡線索、提示 | 唯讀 | 不以外部或模型判定語境 | curated sense 修訂需要 | `canary`、`capsule` 顯示所有義項與提示 |
| `find` 前綴搜尋 | 在不確定拼字時找本機詞條 | 單一 prefix → 排序結果 | 唯讀 | 不做雲端或全文搜尋 | 不需要 | `find roll` 回傳本機 `roll` 結果 |
| 私人 overlay 生命週期 | 保存、確認與清理個人或團隊術語 | 互動新增／明示 list／canonical remove → 終端或 JSON | 只寫 `$XDG_DATA_HOME` 或本機 fallback | 預設 private；list 僅由明示命令讀取；remove 必須 `--yes` 且不做 alias／fuzzy／prefix 刪除 | 使用者自行確認輸入與刪除 | 暫存 XDG 下 add、list、remove 的實際 smoke 通過 |
| shareable-only export | 讓使用者選擇性取出可分享資料 | export flag → JSON stdout | 讀 overlay；不寫 shipped data | 僅顯式 shareable；不 upload | 使用者在 add 時選擇 | private entry 不出現在 export |
| 資料驗證與 canary | 發現 schema、語意與安全回歸 | 驗證命令 → exit code／結果 | 讀本機資料；測試使用暫存資料 | 不 fetch URL、不呼叫 provider | curated data 變更前需要 | unittest、`validate-data`、canary 均通過 |
| curated provenance 驗證 | 記錄未來 curated 資料的來源聲明 | seed entry → provenance verdict | 讀 shipped data；不改 legacy overlay | HTTPS 僅做語法檢查；不等同正確性 | curated 新增／實質修訂需要 | `sourced` 或 `no_public_source` 缺證據即 fail closed |
| 詞條來源可見性與可解釋查詢 | 讓使用者看見本機 provenance 狀態與排名原因 | term／JSON query → provenance 摘要與 match tier | 唯讀 shipped seed 與 overlay | 不開網路、不驗證 URL；private 不外洩來源 | MVP acceptance 審核輸出合約 | legacy、sourced、no-public-source、private 可區分 |
| 有限詞形與模糊搜尋 | 降低英文詞形與單一拼寫差異摩擦 | 單一詞形／距離 1 → 明確標示候選 | 唯讀 | 不傳送 query；不得退化為全文搜尋 | MVP acceptance 審核誤配與排序 | 詞形與距離 1 候選可解釋；`--no-fuzzy` 或 `--exact` 可關閉 |
| 本機資料層狀態 | 確認可用來源但不洩露私人內容 | `sources` → 固定層狀態／JSON | 只讀 layer existence 與 ECDICT schema | 不列出 private entry、不執行 sdcv、不讀專案檔案 | 不需要 | 暫存 XDG 下輸出穩定且不建立 overlay |
| curated-only lookup | 在需要可重現權威層時排除私人／一般詞典結果 | `lookup --curated-only TERM` | 唯讀 shipped seed | 不讀 overlay、不使用 ECDICT、不出網 | 不需要 | private override 不影響 curated-only 結果 |

### MVP acceptance 後的擴展

| 項目 | 使用者價值 | 輸入與輸出 | 本機資料讀寫 | 隱私／安全限制 | 人工審核 | 最小驗收條件 |
| --- | --- | --- | --- | --- | --- | --- |
| Retrieval polish（已完成） | 固化搜尋行為的可理解性與使用者控制 | `--exact`、smoke、錯誤訊息、說明與 JSON 相容性 | 唯讀 | 不新增資料來源、網路或 query 留存 | 已以 CI／實際 smoke 驗證 | 精確模式不接受 inflection／fuzzy；全套測試與 smoke 通過 |
| Curated curation expansion（等待新來源授權） | 在可追溯規則下增加本機詞彙覆蓋 | 固定 curated batch → shipped seed | 寫 shipped seed | 不得 fetch URL；provenance fail closed | 新來源／授權後才可啟動；完成時需 CI／PR 或實際 smoke | schema／provenance／canary／smoke 全通過 |
| 快速工程語意與縮寫 P1–P5（已接受） | 從使用者明示選取的一行英文快速理解工程術語、縮寫與多義項 | selection／單行 → 終端 concise／expanded 或 JSON；限選取的 IDE 入口 | `scan` 只讀 private／curated；private add 只在使用者明示後寫 private overlay | 全離線；無查詢歷史、工作區／檔案／剪貼簿掃描、外部資料、provider 或靜默 fallback | JY 以固定 machine simulation 綠燈接受本 campaign | 詳見 P1–P5 審批包；P5 提供 checked-in WSL Extension Development Host 啟動契約，手動驗收從 `vscode-extension/` 按 F5 進行 |

### 本機詞彙基底分層

| 層級／專案 | 角色 | 目前狀態 | 不可違反條件 |
| --- | --- | --- | --- |
| private overlay | 使用者私有詞彙 | 已實作 | 永遠最優先；不外傳 |
| Englex curated glossary | 工程／AI 繁中語意權威層 | 已實作 | 不由外部一般詞典直接覆蓋 |
| ECDICT | 一般英中離線 fallback 基底 | B1 已實作為明示 local import | 只在前兩層未命中時使用；標示 fallback；可關閉 |
| gen-ai-glossary | AI／工程延伸詞彙候選來源 | B2 已完成固定 curated batch | 只可產生 curated 候選，不能直接覆蓋權威層 |
| sdcv | 可選本機詞典讀取引擎 | B3 已完成 opt-in local adapter | 不是 Englex 詞彙權威或資料來源；不加入正常 lookup 排名 |
| NAER academic terminology | 繁中工程術語候選來源 | 已完成一個 computing CSV 快照的 N1–N4；30 條 `ai_drafted` curated entries 已帶 NAER provenance 匯入 | 僅能以明示選定、可重現的 discipline CSV 快照產生候選；不可整包注入、不可取代 Englex 語意、不可在 runtime 連網 |

工程縮寫是詞條的可解釋語意，而不是未說明的工具代號：命中縮寫時必須顯示已審定全稱、工程義項與歧義狀態；沒有已審定資料時只能明示未知，不能猜測或向外查詢。其完整 P1–P5 規格見 快速工程語意與縮寫審批包。

### 明確延後或排除

| 項目 | 使用者價值 | 輸入與輸出 | 本機資料讀寫 | 隱私／安全限制 | 人工審核 | 最小驗收條件 |
| --- | --- | --- | --- | --- | --- | --- |
| 瀏覽器整合與非選取式 IDE 存取 | 可能降低切換成本 | 編輯器或網頁事件 → UI 結果 | 可能涉及工作區或網頁資料 | P5 僅允許明示 selection 的 VS Code command；仍排除網站注入、剪貼簿與專案檔案讀取 | 非 P5 範圍仍需另立產品與權限審核 | 目前不得實作 |
| 雲端備份／同步 | 跨裝置可用性 | overlay → 遠端副本 | 需讀寫外部服務 | 可能破壞本機私有資料模型 | 需安全、帳號、刪除與成本審核 | 目前不得實作 |
| 外部來源補充 | 擴充詞彙覆蓋 | query／URL → 外部結果 | 可能寫 cache | 破壞離線與 query 隱私保證 | 需來源、授權、快取與審核規則 | 目前不得實作 |
| LLM／Ollama | 可產生說明或候選 | 術語／上下文 → 生成內容 | 可能讀模型或本機資料 | 會改變正確性、資源與隱私邊界 | 需獨立品質與安全審核 | 目前不得實作 |
| 全文翻譯／文件輸入 | 處理長內容 | 文件／段落 → 翻譯 | 會讀使用者文件 | 違反單詞短術語與不讀專案文件邊界 | 需完全不同產品設計 | 目前不得實作 |
| 未授權的縮寫資料補全 | 看似可增加縮寫覆蓋 | 外部資料／猜測 → 全稱 | 可能改動 shipped glossary | 會破壞 curation、provenance 與離線承諾 | 需新資料與 curation 授權 | 目前不得實作 |

## 不可違反的非功能約束

- 預設全離線：不做 HTTP、provider 呼叫、遙測、查詢歷史或專案檔案掃描。
- 此全離線約束只適用於工具 runtime 的資料與查詢邊界；Git、CI、封裝建置與其他明示開發期驗證不屬於 runtime，仍須各自記錄其網路與供應鏈條件。
- 不上傳使用者輸入或 private overlay。
- curated shipped glossary 與 private overlay 的資料權責、驗證方式與分享權限必須分離。
- provenance 是來源紀錄，不等同詞條正確性、人類審查或人類產品驗收。
- englex 自己擁有產品目標、設計與驗收證據，不依賴任何外部編排系統保存任務內容。

## 未來候選功能與拒絕條件

| 候選 | 是否值得做 | 前置條件 | 必須拒絕或延後的時機 | 可能破壞離線／隱私模型 |
| --- | --- | --- | --- | --- |
| 詞形還原 | 已納入 MVP | 固定英文字形規則、可解釋 fixtures、無新依賴 | 不能維持確定性或誤配過高時 | 否，若完全本機 |
| 模糊搜尋 | 已納入 MVP，且限距離 1 | 排序、閾值、結果標示與測試 | 變成不透明猜測或全文搜尋時 | 否，若完全本機 |
| 非選取式 VS Code extension 擴張 | 延後 | P5 以外的新權限、資料讀取或 UI 設計 | 需要網站注入、剪貼簿或專案掃描時 | 可能 |
| 雲端備份 | 現階段不值得 | 可選端對端保護、帳號與刪除政策 | 任一 private overlay 預設上傳或保留不清時 | 是 |
| 外部來源補充 | 現階段不值得 | 離線模式不受影響、來源授權與明示啟用 | 查詢會自動出網或寫外部 cache 時 | 是 |
| LLM／Ollama | 延後 | 可驗證效益、資源模型、輸入界線與人工品質審核 | 以生成內容取代 curated 語意或改變離線承諾時 | 可能 |

## 外部基底 campaign

1. **B1：ECDICT generic fallback（已完成）**：固定來源、明示匯入到本機 SQLite，並只在 private／curated 未命中時提供可關閉的一般詞典結果。
2. **B2：gen-ai-glossary extension candidates（已完成）**：將外部 AI 詞彙作為候選 intake；經 Englex curation 與 provenance 後才可進入權威層。
3. **B3：sdcv optional engine（已完成）**：隔離的本機讀取器；不得改變資料優先序、離線性或 query-history 邊界。
4. **B4：three-role local-base acceptance（已完成）**：以 unit tests、既有 product smoke 與實際 `sdcv` fixture smoke 驗證三個角色不互相越權；這不是文字審查表，也不宣稱任何外部字典內容已被人工驗收。

## v0.4 local-productivity campaign

1. **C0 baseline（已完成）**：記錄固定 Englex 基線；不宣稱產品 acceptance。
2. **C1 local source visibility（已完成）**：新增不讀私人內容的固定資料層狀態輸出。
3. **C2 locked-source coverage（已完成）**：僅以既有 gen-ai-glossary 鎖定來源新增帶 provenance 的小批術語，並擴展既有 sourced term 的低歧義別名。
4. **C3 curated-only control（已完成）**：提供排除 private overlay 與 ECDICT 的顯式查詢模式。
5. **C4 installation acceptance（已接受）**：以無網路、暫存目錄的 local install smoke 驗證 console entry point；JY 已依 CI／實際 smoke 證據接受本 campaign。

## Design Grill re-alignment 與 v0.5 private-overlay-lifecycle campaign

已使用 caller-owned context capsule 完成兩個設計挑戰槽（反證與替代排序）；它是受限的本機設計判讀，不是假稱 provider 審查或 host receipt。完整結論見 design grill realignment。

1. **L0 current-position reset（已完成）**：v0.4 已接受；MVP closure 與 retrieval polish 不再標為目前進行中。既有鎖定來源已完成指定批次，沒有新來源授權時不得自動啟動 curated expansion。
2. **L1 explicit private list（已完成）**：只在使用者明示 `private list` 時讀出 overlay，空 overlay 仍以成功、穩定 JSON 回覆。
3. **L2 canonical private remove（已完成）**：`private remove --yes TERM` 只刪除 canonical 完全相符的私人詞條；alias、fuzzy 與 prefix 都不能刪除。
4. **L3 lifecycle evidence（已完成）**：unit coverage、暫存 XDG 的 lifecycle smoke 與文件合約共同驗證新增、列出、移除與缺失拒絕。
5. **L4 product acceptance（已接受）**：JY 已依 43 個 unit tests、`validate-data` 與實際 private lifecycle smoke 的綠燈接受 v0.5；provider-bound Design Grill 是非阻塞補充，不是 acceptance 閘。

## Campaign 執行順序

1. **v0.5 private overlay lifecycle（已接受）**：已在既有本機資料權責內補齊明示 list 與保守 remove，並以 CI／PR 等價的可重跑實際 smoke 驗收。
2. **快速工程語意與縮寫 P1–P5（已接受）**：JY 已批准整體執行並以固定 machine simulation 綠燈接受。`scan` 只處理使用者明示的一行、最多 200 字元的文字，以 private／curated 的精確 term、alias 與已審定縮寫輸出可解釋結果。P2 明示交接 private add，P3 提供固定排序與 concise／expanded 輸出，P4 記錄模塊組裝，P5 提供選取限定的 VS Code entry。simulation 驗證 source、temporary-XDG、offline install 與 VS Code adapter；完整範圍與停止契約見 P1–P5 審批包。
3. **Curated curation expansion（等待新來源授權）**：OS3 與已完成的 NAER computing batch 不構成持續擴充授權；後續僅在明示提供可用來源、授權與固定批次後，以既有 provenance 進入小批 curation，不得以自動網路取得替代授權。
4. **NAER terminology intake（computing N1–N4 已完成；其他學科等待 N1 明示批准）**：已完成的 computing 快照、delta、草稿與 JY 接受批次已匯入 30 條 `ai_drafted` entries。其他學科仍須依 [NAER candidate-source specification](external-sources/naer-academic-terminology.md) 取得一個明示學科的可重現快照與 delta；只有 N3 的人工批次接受才可改動 curated seed。這不改變 runtime 離線邊界。
5. **其他擴展**：任何 UI、同步、外部查詢、provider、檔案輸入或新依賴，皆需獨立產品與權限 campaign，不得從本機 lifecycle 工作單元外溢。

MVP acceptance 以 [測試計畫](test-plan.md) 的 CI／PR 命令與實際 smoke 為準。未通過前，不得自動進入下一個會改變產品行為的 campaign。
