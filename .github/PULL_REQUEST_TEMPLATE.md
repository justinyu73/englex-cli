<!-- 先讀 CONTRIBUTING.md。離線／隱私是硬約束。 -->

## 修訂範圍
<!-- 這個 PR 改了什麼、為什麼。 -->

## 可檢查證據
<!-- 審查連結、來源 URL、或可讓維護者重跑 smoke 的說明。 -->

## 檢查清單
- [ ] 未新增 runtime 網路、查詢記錄、雲端同步或 runtime 依賴；未把外部雙語標籤直接當繁中定義。
- [ ] 新詞條標為 `ai_drafted`，`senses` 有原創繁中解釋、`domain`、`context_triggers`、`context_required`。
- [ ] `provenance` 用可檢查的 HTTPS `source_url`，或 `no_public_source` + 非空 reason。
- [ ] 若升級信任等級：附完整 `attribution`（`upgraded_by` / `evidence` / `date`）；未濫用 `grandfathered`。
- [ ] 已在本機跑並通過：
  - [ ] `python3 -B -m englex validate-data`
  - [ ] `sh tests/glossary-schema-smoke.sh`、`sh tests/trust-level-smoke.sh`
  - [ ] `python3 -B -m unittest discover -s tests -v`
  - [ ] `python3 -B tests/p1_p5_machine_acceptance.py`
- [ ] 草稿未在人工接受前 import 到 `englex/seed_data.json`（若適用）。
