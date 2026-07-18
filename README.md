# englex v0.6

`englex` 是給 WSL／VS Code 終端機使用的離線優先英語 AI／軟體工程術語小詞典。它幫你在讀一行程式、設定、發布說明或技術文案時，快速理解裡面 AI／工程術語的**領域意思**——目的是「學會這個詞在工程脈絡下代表什麼」，不是做語言學上精準的翻譯。查詢只讀本機資料，不替你蒐集或傳送查詢內容。

## 為什麼在本機、為什麼不走雲端

工程術語幾乎都嵌在你的實際工作裡：專案程式碼、設定檔、commit 訊息、產品文案。這些內容你通常不會、也不該整段丟給雲端翻譯。更關鍵的是，同一個詞在同一行會因脈絡指向完全不同的意思——`canary` 可能是發布通道、漸進流量驗證或監測測試；`seed` 可能是隨機種子或資料來源。直接翻譯很容易掉進字面義（金絲雀、種子）而失去工程語境。Englex 把你明示交給它的一行文字對照本機 curated 詞條，保留英文術語、繁中工程解釋、來源與信任等級，讓你自己判讀，而不是把內容送出去或交給不透明的翻譯。

## 上下文消歧（核心）

同一個詞會因同一行的線索指向不同義項。`scan` 以確定性的 `context_triggers` 比對同一行其餘文字，公開標示「最可能義項」與命中的線索；所有義項仍會完整列出，不會被隱藏。

```bash
englex scan "roll out canary to 5% traffic"
# canary：最可能義項 2（命中線索：traffic）

englex scan "install from canary channel nightly"
# canary：最可能義項 1（命中線索：channel, nightly）

englex scan "the canary sang"
# canary：上下文判定：無法由上下文判定
```

## 給誰用／適用環境

Englex 針對 **VS Code／終端機（WSL）** 的開發流程設計：你在編輯器或 shell 裡遇到看不懂的術語，選取或貼一行、當場查、不切換情境。如果你的場景是**網頁瀏覽、AI 桌面應用或一般聊天**，市面上已有更整合的工具；Englex 不打算取代它們，只專注做好終端機裡的術語查詢這件事。

## 可擴充：一份會長大的工程術語表

AI／工程術語持續在演化——例如 `harness`（字面是馬鞍具）近來才被 AI 圈賦予「驅動模型執行的框架」這種特殊意思。Englex 設計成能隨這類新詞成長：新增或修訂詞條都保留來源與信任等級（見下），既收得進剛出現的術語，也讓你看得出哪些還是草稿、哪些已審定。

## 威脅模型與隱私

本工具的設計目標是避免把查詢術語、私人註記或使用行為交給第三方。核心 lookup 不含 HTTP 用戶端、網路函式庫、子程序呼叫、遙測、分析或查詢歷史；查詢結果也不寫入磁碟。唯一例外是使用者明確呼叫 `lookup-sdcv` 時，才以隔離環境執行已安裝的本機 `sdcv`。它不保護已遭入侵的主機、你的家目錄檔案權限，或你主動將輸出貼到其他地方的情況。私人 overlay 的保護仍取決於本機帳號與檔案系統權限。

## 信任等級：把草稿、社群與既有資料說清楚

每個 curated lookup／scan 結果都會顯示 `trust_level`。這不是正確性保證，而是讓你在看到釋義前就能分辨資料目前的審定狀態，避免把 AI 草稿、社群修訂與歷史隨附內容混為一談：

| 等級 | 意義 |
| --- | --- |
| `ai_drafted` | AI 草擬、尚未人工審定的原創繁中工程解釋。 |
| `community` | 開源貢獻者提供或修訂，尚未經維護者審定。 |
| `maintainer_verified` | 維護者／專家審定。未來升級時會保留升級人、證據與日期。 |
| `legacy` | 既有隨附、未回溯驗證的歷史資料。 |

這個標示是 Englex 的可檢查信任邊界：使用者可自行決定某一條目是否適合直接採用、是否要查來源，或是否值得協助審閱升級。`provenance` 仍只描述來源，不等同正確性或人工驗收。

## 功能 Demo

見 [docs/DEMO.md](docs/DEMO.md)，包含上下文消歧、信任等級、wishlist 迴圈與 VS Code 手動錄製 TODO。

## 使用方式

在專案目錄中可直接執行：

```bash
python3 -m englex canary
python3 -m englex lookup "canary deployment"
python3 -m englex find roll
python3 -m englex lookup --json canary
python3 -m englex lookup --json --explain provenance
python3 -m englex lookup --json --explain embeding
python3 -m englex lookup --no-fuzzy embeding
python3 -m englex lookup --exact embedding
python3 -m englex lookup --curated-only canary
python3 -m englex sources --json
python3 -m englex private list --json
python3 -m englex private remove --yes "my private term"
python3 -m englex import-ecdict /path/to/ecdict.csv
python3 -m englex lookup-sdcv --data-dir /path/to/stardict-root zorb
python3 -m englex find --json roll
python3 -m englex scan --json "Use canary deployment with SLO and sdcv"
python3 -m englex scan --format concise "Use canary deployment with SLO and sdcv"
python3 -m englex private add --term "team release" --abbreviation TR --full-name "Team Release"
python3 -m englex validate-data
```

最常用的快速理解方式是把一行文字明示交給 `scan`；它只分析這個 argument，不讀剪貼簿、stdin、檔案或工作區：

```bash
englex scan "Use canary deployment with SLO and sdcv"
```

要安裝到目前 Python 環境並取得 `englex` 指令，可自行在可信任的本機環境執行：

```bash
python3 -m pip install .
englex embedding
```

## 本機／私下 wheel 散佈

Englex 不發佈到 PyPI 或 VS Code Marketplace。交付 wheel 前，在 source checkout 中建立暫存工作目錄；這會安裝開發期的 PyPA `build`，不會加入 Englex 的 runtime 依賴：

```bash
source_dir="$(pwd)"
work_dir="$(mktemp -d)"
python3 -m venv "$work_dir/build-tools"
"$work_dir/build-tools/bin/python" -m pip install build
(
  cd "$work_dir"
  "$work_dir/build-tools/bin/python" -m build --outdir "$work_dir/dist" "$source_dir"
)
```

`$work_dir/dist/` 會包含 `.whl` 與 `.tar.gz`。把 wheel 私下交付後，接收端可建立自己的 venv 並直接安裝該檔案；這不是 `pip install .`：

```bash
python3 -m venv "$HOME/.local/share/englex/venv"
"$HOME/.local/share/englex/venv/bin/python" -m pip install --no-deps /path/to/englex-*.whl
"$HOME/.local/share/englex/venv/bin/englex" lookup --exact embedding
```

若接收端已安裝 [pipx](https://pipx.pypa.io/)，也可從同一份私下 wheel 安裝：

```bash
pipx install /path/to/englex-*.whl
englex lookup --exact embedding
```

上述步驟不會將 Englex 或查詢內容發佈、上傳或同步；runtime 仍只讀本機資料。

新增詞條只接受互動式提示，且預設為私人：

```bash
englex add
```

私人 overlay 的內容只會在明確管理命令下讀出；`private list` 可列出目前的私人詞條，`private remove --yes TERM` 只刪除 canonical 完全相符的詞條，不以 alias、模糊或前綴擴大刪除範圍。`scan` 的未命中只會提供 `private add --term TERM` 的明示交接；實際新增仍要求使用者填寫定義、領域、狀態與分享權限。`private add` 亦可明示傳入已審定的 private 縮寫與全稱。它們都只操作本機 overlay，不上傳、不同步，也不建立查詢歷史。

若你想累積日後要補的術語，可明示開啟 miss wishlist：**這是你的個人 wishlist，本機、預設關、可清。** 開啟後，只有一般 `lookup` 完全查不到的術語會寫入 `$XDG_DATA_HOME/englex/wishlist.json`；它只存該術語，不存整行、上下文、時間或查詢歷史。`scan` 不會寫入 wishlist。也可隨時用 `wishlist add TERM` 手動排入一詞：這是明示動作，不受 `enabled` 影響；即使該詞已在詞庫，也會照使用者意願加入並提示「已在詞庫，補批會跳過」。

```bash
englex wishlist enable
englex lookup "an unknown engineering term"
englex wishlist add "some term"
englex wishlist list --json
englex wishlist clear --yes
englex wishlist disable
```

只有新增時明確回答 `yes` 的詞條才會出現在下列輸出；此命令只輸出 JSON 到終端，不會上傳：

```bash
englex export --shareable-only
```

查詢限為 1–5 個詞、80 個字元內、單行且非句子；這讓工具維持術語查詢，而非翻譯器。

## 資料位置

隨附的人工詞條位於套件中的 `englex/seed_data.json`，不會被修改。使用者資料只寫入：

- `$XDG_DATA_HOME/englex/overlay.json`
- `$XDG_DATA_HOME/englex/wishlist.json`（使用者明示開啟 miss 記錄或手動 `wishlist add` 後）
- 未設定 `XDG_DATA_HOME` 時：`~/.local/share/englex/overlay.json` 與（使用者明示開啟 miss 記錄或手動 `wishlist add` 後）`~/.local/share/englex/wishlist.json`

## 已知限制與延後範圍

v0.6 的一個術語可包含多個可能義項、脈絡線索與「需要上下文」標記。查詢排名固定為：使用者 overlay 的 canonical 精確匹配、隨附資料的 canonical 精確匹配、別名、已知本機詞條的有限詞形還原、距離 1 的單詞候選、前綴匹配；scan 會依上下文公開標出最可能義項並說明命中線索，但仍列出全部、不隱藏其他。`--json` 會輸出 `schema_version`、`results` 與本機 ranking／provenance 說明；`--explain` 可在終端卡片顯示排名原因。若不想接受距離 1 候選，可用 `lookup --no-fuzzy TERM` 關閉；若只接受 canonical／alias 精確匹配，使用 `lookup --exact TERM`。`lookup --curated-only TERM` 會排除 private overlay 與 ECDICT，只讀隨附 curated glossary。`englex sources` 只回報各層可用狀態，不讀或顯示私人詞條。來源紀錄不等同正確性或人類驗收。

本機資料可用下列命令驗證 schema、重複 canonical／alias、必填欄位與 context-required 記錄：

```bash
python3 -m englex validate-data
```

## Curated glossary source provenance

未來新增或實質修訂的 curated 詞條必須保留有效 HTTPS 來源 URL，或明確記錄不適用公開來源的理由。這是 entry-level provenance 驗證，不等同正確性、人類審查或產品驗收；既有 seed 詞條明確屬於 legacy，並未因此被追溯驗證。private overlay 維持本機私有 provenance。詳見 [glossary source provenance policy](docs/glossary-source-provenance-policy.md)。

### NAER 出處

部分 `ai_drafted` 的 computing 詞條以國家教育研究院（NAER）「兩岸對照名詞－資訊」資料集作為候選來源與 provenance：[`data.gov.tw/dataset/15275`](https://data.gov.tw/dataset/15275)，授權為[政府資料開放授權條款第 1 版](https://data.nat.gov.tw/license)。NAER 的英中標籤不會直接當作 Englex 定義；隨附的繁中工程解釋仍為 Englex 原創草擬，並保留其 `ai_drafted` 信任等級直到人工升級。完整 intake 邊界見 [NAER academic terminology candidate-source specification](docs/external-sources/naer-academic-terminology.md)。

本版提供有限、可關閉的詞形還原與距離 1 模糊搜尋，以及 `scan`：它只接受使用者以 argument 明示交付的一行、最多 200 字元文字，並只做 private／curated 的 canonical、alias 與受控縮寫精確比對。它不會混入 ECDICT、sdcv、詞形或 fuzzy 結果。完整的現在／擴展／延後範圍與 campaign 順序見 [產品功能地圖](docs/product-feature-map.md)；MVP acceptance 仍以 CI／PR 功能通過及實際 smoke 為準。瀏覽器整合、雲端同步、外部查詢、Ollama/LLM、剪貼簿／stdin／檔案輸入、全文翻譯、上傳與遙測仍明確延後。

## Optional VS Code lookup entry

`vscode-extension/` contains a dependency-free P5 entry. **Englex: Look Up Engineering Term** opens an input box, and the always-visible **Englex** status-bar button and `Ctrl+Alt+L` (`Cmd+Alt+L` on macOS) invoke that same command. The input-box command sends only the text you personally type or paste through local `englex scan --json`; it does not automatically read the clipboard, terminal, editor, workspace, files, network, telemetry, or accounts. The editor-selection command remains available with `Ctrl+Alt+E` and its context menu. Both the selection version and input-box version do not touch the clipboard; user pressing Ctrl+V into the input box is still just input-box text. Query text is discarded after use and not persisted, uploaded, or historized. See its [local extension instructions](vscode-extension/README.md).

The extension also makes known terms in terminal output clickable. This terminal-link feature scans terminal output one line at a time locally and marks only terms returned by the local Englex glossary as links; each line is compared in memory only, never written to disk, uploaded, historized, or read from the clipboard. Hover 即顯示定義，點擊則開啟完整 Englex 解釋面板。This reads a larger surface than an input box that sees only what you type, so decide for yourself whether that terminal integration fits your privacy preference.

When either VS Code entry gets a complete miss for a one-line term-shaped input of at most five words and 80 characters, it offers **找不到「<文字>」，加入 wishlist？**. Only an explicit click on **加入 wishlist** runs local `englex wishlist add <文字>`; long sentence-like misses do not trigger the prompt.

## Optional ECDICT fallback base

ECDICT is an optional local general English-Chinese fallback, not an engineering glossary authority. After obtaining its CSV separately, import it explicitly:

```bash
python3 -m englex import-ecdict /path/to/ecdict.csv
python3 -m englex lookup an-unknown-general-word
python3 -m englex lookup --no-fallback an-unknown-general-word
```

The import creates `$XDG_DATA_HOME/englex/ecdict.sqlite` (or the normal local-data fallback) and does not modify the private overlay or shipped glossary. Lookup order is private overlay, Englex curated glossary, then ECDICT only if neither local layer matches. `--no-fallback` disables it. The source lock, attribution, and offline boundary are in [ECDICT B1 source lock](docs/external-sources/ecdict.md).

## Optional local StarDict engine

`lookup-sdcv` is separate from the normal lookup path. It only reads a directory explicitly passed as `--data-dir`, which must contain `dic/`, and it never changes the private／curated／ECDICT ranking or imports dictionary content into Englex:

```bash
python3 -m englex lookup-sdcv --data-dir /path/to/stardict-root zorb
python3 -m englex lookup-sdcv --json --data-dir /path/to/stardict-root zorb
```

It runs the installed `sdcv` with exact matching, only that data directory, a disposable home directory, no inherited environment, and history disabled. A selected StarDict result is labelled `local_external`, not curated. The adapter does not download or prescribe a third-party dictionary dataset; see the [sdcv B3 source lock](docs/external-sources/sdcv.md) and run `sh tests/sdcv-smoke.sh` after installing `sdcv` for the real local-engine smoke.

## 驗證

```bash
python3 -B tests/p1_p5_machine_acceptance.py
python3 -m unittest discover -s tests -v
python3 -m englex canary
python3 -m englex "canary deployment"
python3 -m englex find roll
python3 -m englex capsule
python3 -m englex lookup --json canary
sh tests/smoke.sh
sh tests/install-smoke.sh
sh tests/private-lifecycle-smoke.sh
python3 -m englex validate-data
```

專案程式與隨附資料均以 [MIT License](LICENSE) 發布。
