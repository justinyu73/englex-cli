# Changelog

本檔記錄值得注意的變更，格式參考 [Keep a Changelog](https://keepachangelog.com/)。
本專案在 1.0 前，minor 版本可能包含破壞性變更。Englex 不發佈到 PyPI 或 VS Code Marketplace；release 以 [GitHub Releases](https://github.com/justinyu73/englex-cli/releases) 交付 wheel／sdist／vsix。

## [Unreleased]

### Fixed
- VS Code 狀態列補批數字改為點擊當下以即時 `wishlist list` 校正（不再停留在視窗啟動時的舊值）；tooltip 補上括號數字是淨新待翻詞數的說明。

## [0.7.0] - 2026-08-01 — VS Code 補批按鈕與 dev-time AI 翻譯補批

### Added
- **Wishlist AI 翻譯補批（dev-time curation）**：`tools/wishlist_draft.py auto`——由維護者手動觸發（無數量門檻，≥1 淨新詞即跑，批次由人決定），以維護者自己的 `ANTHROPIC_API_KEY`（repo 根 `.env`，永不 commit）呼叫線上模型草擬，沿用 `merge` 的 ai_drafted-only 驗證、canonical/alias 去重、surgical append-only 併入與失敗回滾；零淨新詞為離線 no-op。不進 wheel，查詢 runtime 維持全離線。實際 API 補批為人工驗收項（需憑證），同 VSIX smoke。
- **VS Code 補批按鈕**：`Englex: Translate Wishlist Batch` 指令與狀態列 `$(sync) Englex 補批`（顯示淨新待翻數）；需設定 `englex.maintainerRepo` 指向本機 englex-cli checkout，確認後執行上述 `auto`，併入成功可一鍵 `python3 -m pip install --user` 重裝讓新詞條生效（PEP 668 externally-managed 環境自動加 `--break-system-packages` 重試一次，仍只動 `~/.local`）。

### Fixed
- `.gitignore` 補強防呆：新增 `node_modules/`、`dist/`、`out/`、`.env`、`.env.*`（保留 `!.env.example`）、`*.log`、`*.sqlite`、`*.db`；移除 loop-hybrid 遺留的 `runtime/` 條目。
- 清掉三處指向未隨公開化釋出檔案（詞彙挖掘工具、Chain C 規格、擴充 UX 文件）的死路徑引用。

## [0.6.0] - 2026-07-15 — Chain C 需求迴圈與 VS Code 點選表面

### Added
- **Chain C 詞庫更新供應鏈**：opt-in 本機 miss wishlist（`wishlist enable/disable/add/list/clear`）——查不到自動記或手動排入，只存詞、不外傳、預設關；dev-time 補批工具 `tools/wishlist_draft.py`（`brief` 出草擬清單、`merge` 驗 ai_drafted 後 append-only 併入並清 wishlist），不進 wheel。
- **VS Code 擴充點選表面**：輸入框查詢 + 狀態列 `📖 Englex` 按鈕 + `Ctrl+Alt+L`（零剪貼簿，只看你輸入的字）；查不到一鍵加入 wishlist（術語形狀 guard 擋長句）；終端機可點連結（逐行本機比對詞庫）；終端機 hover 直接顯示定義。
- 擴充輸出從只印匹配升級為顯示完整義項定義、信任等級與最可能義項。
- dev-time 詞彙挖掘輔助（掃本機 transcript 抽候選詞、對詞庫去重）；屬維護者私有工具，未收進公開 repo。

### Changed
- README 開場重構為「本機情境化 AI／工程術語理解」定位。

### Docs
- Chain C 規格與擴充 UX 決策（hover 比較、平台限制）留於維護者私有 repo，未隨公開化釋出。

### Notes
- 護城河哲學：需求塑形（miss）× AI 供給（ai_drafted）× 本機累積；個人詞彙有限，飽和後維護趨零。真正的「浮球」浮動覆蓋層非 VS Code 能力範圍。

## [0.5.0] - 2026-07-14 — open-source readiness

### Added
- 上下文消歧 `scan`：以確定性 `context_triggers` 比對同一行其餘文字，公開標示最可能義項並列出全部。
- 誠實 `trust_level` 系統（`maintainer_verified` / `community` / `ai_drafted` / `legacy`），terminal 卡片與 `--json` 皆顯示。
- 常見系統／流程術語批次（44 條，字面易誤解為主）；curated 詞條達 118 條、legacy 32 條。
- opt-in 外部層：NAER computing 候選來源 intake、ECDICT 一般 fallback、sdcv StarDict 本機引擎（皆需明示啟用，不混入 curated 排名）。
- 私下 wheel／pipx 散佈流程；selection-only VS Code entry（`vscode-extension/`）。
- dev-time 詞彙挖掘輔助（掃本機 transcript 抽反引號詞、對詞庫去重）：不進 wheel、離線、不寫入詞庫；屬維護者私有工具，未收進公開 repo。
- GitHub Actions CI：push／PR 到 `main` 時跑 `validate-data` + `unittest` + P1–P5 機器驗收 + smoke 套件。

### Changed
- README 開場重構為「本機情境化 AI／工程術語理解」定位（為什麼在本機／給誰用／可擴充），隱私威脅模型降為邊界段。
- 信任升級改為必填 `attribution`（`upgraded_by` / `evidence` / `date`）；`grandfathered` 僅保留給既有 12 條歷史 seed。

### Fixed
- 修復 3 支潛伏的爛測試（`trust-level-smoke`、`glossary-schema-smoke`、`naer-computing-n3b-draft-smoke`）：改測試不改規則，全套轉綠。

### Security / Privacy
- 核心 lookup 不含 HTTP 用戶端、網路、子程序、遙測、分析或查詢歷史；查詢結果不落地。唯一例外是使用者明示呼叫 `lookup-sdcv`。
