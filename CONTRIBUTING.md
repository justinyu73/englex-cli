# Contributing to Englex

Englex 是離線、無遙測的本機工程術語工具。貢獻不得新增 runtime 網路、查詢記錄、雲端同步或 runtime 依賴，也不得把外部雙語標籤直接當作繁中定義。

## 新增詞條：從 `ai_drafted` 開始

新增 curated 詞條預設為 `ai_drafted`。請在草稿 fixture 中提供現行 schema 的 `term`、`aliases`、`senses`、`status`、`provenance` 與 `trust_level`：

- `senses` 要有原創的繁中工程解釋與 `domain`。
- `provenance` 使用可檢查的 HTTPS `source_url`；來源是候選或證據，不是定義的逐字來源，也不是正確性保證。
- `trust_level` 設為 `ai_drafted`，等待人工抽查。不要因為有來源 URL 就直接標為 `community` 或 `maintainer_verified`。
- 執行 `sh tests/glossary-schema-smoke.sh`、`sh tests/trust-level-smoke.sh`、`python3 -B -m unittest discover -s tests -v` 與 `python3 -B tests/p1_p5_machine_acceptance.py`。

草稿經人工接受前，不得 import 到 `englex/seed_data.json`。

## 升級信任等級

把已接受的 `ai_drafted` 條目升為 `community` 或 `maintainer_verified` 時，保留原創定義與 provenance，並新增完整 attribution：

```json
"attribution": {
  "kind": "upgrade",
  "upgraded_by": "貢獻者或審定者名稱",
  "evidence": "審查連結或可檢查的說明",
  "date": "YYYY-MM-DD"
}
```

`community` 表示社群提供或修訂、尚未由維護者審定；`maintainer_verified` 表示維護者／專家已審定。兩者都需要上述 attribution。`ai_drafted` 與 `legacy` 不需要 attribution。`{"kind":"grandfathered","note":"原始 seed,無正式升級紀錄"}` 僅保留給既有 12 條歷史 seed，不能套用到新詞或新升級。

變更前先跑 `sh tests/trust-level-smoke.sh`；它會拒絕缺少 attribution 的新公開升級。請在提交說明中交代修訂範圍與可檢查證據，讓維護者能重跑 smoke 後決定是否接受。

投稿請開 PR，附修訂範圍與可檢查證據。
