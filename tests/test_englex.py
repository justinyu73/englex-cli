import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from englex import cli, core
from englex import sdcv
from englex.core import QueryError, find, lookup, scan_line, validate_query, validate_scan_text
from englex.data import overlay_path, raw_user_entries, save_user_entries, seed_entries, user_entries, validate_entries, wishlist_path


class EnglexTests(unittest.TestCase):
    def setUp(self):
        self.temp_data_home = tempfile.TemporaryDirectory()
        self.xdg_patch = patch.dict(os.environ, {"XDG_DATA_HOME": self.temp_data_home.name})
        self.xdg_patch.start()

    def tearDown(self):
        self.xdg_patch.stop()
        self.temp_data_home.cleanup()

    def test_canary_is_engineering_release_semantics(self):
        entry = lookup("canary")[0]
        definitions = [sense["definition"] for sense in entry["senses"]]
        self.assertEqual(len(definitions), 3)
        self.assertTrue(any("發布通道" in definition for definition in definitions))
        self.assertTrue(any("deployment" in definition for definition in definitions))
        self.assertTrue(any("test" in definition for definition in definitions))

    def test_capsule_preserves_multiple_uncertain_senses(self):
        entry = lookup("capsule")[0]
        self.assertEqual(len(entry["senses"]), 3)
        self.assertTrue(all(sense["context_required"] for sense in entry["senses"]))

    def test_alias_lookup(self):
        entry = lookup("RAG")[0]
        self.assertEqual(entry["term"], "retrieval augmented generation")
        self.assertEqual(lookup("function calling")[0]["term"], "tool calling")

    def test_lookup_normalizes_case_and_whitespace(self):
        entry = lookup("  Context   WINDOW  ")[0]
        self.assertEqual(entry["term"], "context window")

    def test_inflection_lookup_is_bounded_and_explainable(self):
        entry = {"term": "deployment", "aliases": [], "status": "常用", "provenance": {"version": 1, "kind": "legacy"}, "senses": []}
        with patch.object(core, "user_entries", return_value=[]), patch.object(core, "seed_entries", return_value=[entry]):
            self.assertEqual(core.lookup("deployments")[0]["term"], "deployment")
            self.assertEqual(core.explain_lookup("deployments")[0]["match"], "shipped_canonical_inflection")
            self.assertEqual(core.lookup("deployments", allow_inflection=False, allow_fuzzy=False), [])

    def test_fuzzy_lookup_is_bounded_explainable_and_optional(self):
        entry = {"term": "deployment", "aliases": [], "status": "常用", "provenance": {"version": 1, "kind": "legacy"}, "senses": []}
        with patch.object(core, "user_entries", return_value=[]), patch.object(core, "seed_entries", return_value=[entry]):
            self.assertEqual(core.lookup("deploymnt")[0]["term"], "deployment")
            self.assertEqual(core.explain_lookup("deploymnt")[0]["match"], "shipped_canonical_fuzzy")
            self.assertEqual(core.lookup("deploymnt", allow_fuzzy=False), [])
            self.assertEqual(core.lookup("deploxmnt"), [])

    def test_prefix_search(self):
        results = find("roll")
        self.assertEqual([entry["term"] for entry in results], ["roll forward", "rollback", "rollover"])

    def test_ranking_prefers_user_then_seed_then_aliases(self):
        user = {"term": "canary", "aliases": ["user alias"], "status": "私人", "senses": []}
        seed = {"term": "canary", "aliases": ["seed alias"], "status": "常用", "senses": []}
        alias = {"term": "other", "aliases": ["canary"], "status": "常用", "senses": []}
        with patch.object(core, "user_entries", return_value=[user]), patch.object(core, "seed_entries", return_value=[seed, alias]):
            self.assertEqual(
                [(entry["term"], entry["status"]) for entry in lookup("canary")],
                [("canary", "私人"), ("canary", "常用"), ("other", "常用")],
            )

    def test_overlong_and_sentence_are_rejected(self):
        with self.assertRaises(QueryError):
            validate_query("x" * 81)
        with self.assertRaises(QueryError):
            validate_query("please explain what a canary deployment means to me")
        with self.assertRaises(QueryError):
            validate_query("Canary deployment is safe.")

    def test_scan_accepts_one_explicit_line_but_rejects_multiline_or_overlong_input(self):
        self.assertEqual(validate_scan_text("Canary deployment is safe."), "Canary deployment is safe.")
        with self.assertRaises(QueryError):
            validate_scan_text("canary\ndeployment")
        with self.assertRaises(QueryError):
            validate_scan_text("x" * 201)

    def test_scan_uses_longest_exact_non_overlapping_private_and_curated_matches(self):
        scan = scan_line("Use canary deployment with SLO and sdcv")
        self.assertEqual([(result["start"], result["end"], result["entry"]["term"], result["match_type"]) for result in scan["results"]], [
            (4, 21, "canary deployment", "canonical"),
            (27, 30, "service level objective", "alias"),
            (35, 39, "sdcv", "abbreviation"),
        ])
        self.assertEqual(scan["results"][2]["entry"]["abbreviation"]["full_name"], "StarDict Console Version")
        self.assertEqual([result["entry"]["trust_level"] for result in scan["results"]], ["legacy", "legacy", "maintainer_verified"])
        self.assertEqual([item["text"] for item in scan["unmatched"]], ["Use", "with", "and"])
        self.assertEqual(scan["unmatched"][0]["private_add"], {"command": "private add", "term": "Use"})

    def test_scan_context_ranking_selects_unique_matching_sense(self):
        release = scan_line("canary traffic rollout")["results"][0]["entry"]["context_ranking"]
        test = scan_line("canary test monitor")["results"][0]["entry"]["context_ranking"]
        self.assertEqual(release["decision"], "most_likely")
        self.assertEqual(release["most_likely_sense_number"], 2)
        self.assertEqual(release["matched_triggers"], ["traffic", "rollout"])
        self.assertEqual(test["decision"], "most_likely")
        self.assertEqual(test["most_likely_sense_number"], 3)
        self.assertEqual(test["matched_triggers"], ["test", "monitor"])

    def test_scan_context_ranking_keeps_ambiguous_senses_visible(self):
        scan = scan_line("canary unrelated")
        entry = scan["results"][0]["entry"]
        self.assertEqual(entry["context_ranking"]["decision"], "undetermined")
        self.assertIsNone(entry["context_ranking"]["most_likely_sense_number"])
        self.assertEqual(len(entry["senses"]), 3)
        self.assertIn("上下文判定：無法由上下文判定", core.format_scan(scan))
        tied = scan_line("canary traffic test")["results"][0]["entry"]["context_ranking"]
        self.assertEqual(tied["decision"], "undetermined")
        self.assertIsNone(tied["most_likely_sense_number"])

    def test_scan_prefers_private_exact_match_and_never_uses_generic_fallback(self):
        save_user_entries([{
            "term": "canary deployment",
            "aliases": [],
            "domain": "測試",
            "definition": "私人語意",
            "status": "私人",
            "abbreviation": {
                "short": "teamcanary",
                "full_name": "Team Canary Deployment",
                "display_name": "teamcanary",
                "kind": "team_release",
                "context_required": False,
            },
        }])
        scan = scan_line("canary deployment teamcanary zorb")
        self.assertEqual([(result["entry"]["term"], result["entry"]["source_layer"], result["match_type"]) for result in scan["results"]], [
            ("canary deployment", "private", "canonical"),
            ("canary deployment", "private", "abbreviation"),
        ])
        self.assertEqual([item["text"] for item in scan["unmatched"]], ["zorb"])
        self.assertNotIn("source_url", scan["results"][0]["entry"]["provenance"])

    def test_scan_cli_has_stable_json_and_concise_output(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["scan", "--json", "Use canary deployment with SLO"]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["input"], "Use canary deployment with SLO")
        self.assertEqual([result["entry"]["term"] for result in payload["results"]], ["canary deployment", "service level objective"])
        self.assertEqual([result["entry"]["trust_level"] for result in payload["results"]], ["legacy", "legacy"])
        output.seek(0)
        output.truncate(0)
        with redirect_stdout(output):
            self.assertEqual(cli.main(["scan", "--format", "concise", "canary deployment"]), 0)
        self.assertIn("canonical／curated", output.getvalue())
        output.seek(0)
        output.truncate(0)
        with redirect_stdout(output):
            self.assertEqual(cli.main(["scan", "sdcv"]), 0)
        self.assertIn("StarDict Console Version", output.getvalue())
        self.assertIn("信任等級：maintainer_verified", output.getvalue())

    def test_export_includes_only_explicitly_shareable_entries(self):
        save_user_entries([
            {"term": "private term", "shareable": False},
            {"term": "shared term", "shareable": True},
        ])
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["export", "--shareable-only"]), 0)
        exported = json.loads(output.getvalue())
        self.assertEqual([item["term"] for item in exported], ["shared term"])

    def test_private_list_and_remove_require_explicit_canonical_term(self):
        save_user_entries([
            {"term": "private term", "aliases": ["private alias"], "domain": "測試", "definition": "私人", "status": "私人"},
            {"term": "other term", "aliases": [], "domain": "測試", "definition": "保留", "status": "私人"},
        ])
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["private", "list", "--json"]), 0)
        self.assertEqual([entry["term"] for entry in json.loads(output.getvalue())["results"]], ["private term", "other term"])
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["private", "remove", "--yes", "private alias"]), 1)
        self.assertIn("canonical 完全相符", errors.getvalue())
        self.assertEqual([entry["term"] for entry in raw_user_entries()], ["private term", "other term"])
        with redirect_stdout(StringIO()):
            self.assertEqual(cli.main(["private", "remove", "--yes", "PRIVATE TERM"]), 0)
        self.assertEqual([entry["term"] for entry in raw_user_entries()], ["other term"])

    def test_private_list_is_successful_when_overlay_is_empty(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["private", "list", "--json"]), 0)
        self.assertEqual(json.loads(output.getvalue()), {"schema_version": 2, "results": []})
        self.assertFalse(overlay_path().exists())

    def test_lookup_does_not_create_overlay(self):
        self.assertFalse(overlay_path().exists())

    def test_wishlist_is_opt_in_and_stores_only_lookup_miss_terms(self):
        self.assertFalse(wishlist_path().exists())
        with redirect_stderr(StringIO()):
            self.assertEqual(cli.main(["lookup", "wishlist missing term"]), 1)
        self.assertFalse(wishlist_path().exists())

        with redirect_stdout(StringIO()):
            self.assertEqual(cli.main(["wishlist", "enable"]), 0)
        with redirect_stderr(StringIO()):
            self.assertEqual(cli.main(["lookup", "wishlist missing term"]), 1)
        payload = json.loads(wishlist_path().read_text(encoding="utf-8"))
        self.assertEqual(payload, {"enabled": True, "terms": ["wishlist missing term"]})
        self.assertNotIn("input", payload)
        self.assertNotIn("history", payload)

        with redirect_stdout(StringIO()):
            self.assertEqual(cli.main(["scan", "wishlist missing term in a selected line"]), 0)
        self.assertEqual(json.loads(wishlist_path().read_text(encoding="utf-8")), payload)

        with redirect_stdout(StringIO()):
            self.assertEqual(cli.main(["wishlist", "clear", "--yes"]), 0)
        self.assertEqual(json.loads(wishlist_path().read_text(encoding="utf-8")), {"enabled": True, "terms": []})

    def test_sources_reports_layer_state_without_reading_private_entries(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["sources", "--json"]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["layers"], [
            {"id": "private_overlay", "state": "not_installed"},
            {"id": "englex_curated", "state": "available"},
            {"id": "ecdict_fallback", "state": "not_installed"},
            {"id": "sdcv", "state": "explicit_only"},
        ])
        self.assertFalse(overlay_path().exists())
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["canary"]), 0)
        self.assertFalse(overlay_path().exists())

    def test_unknown_lookup_returns_one_and_writes_stderr(self):
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["unknown engineering term"]), 1)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("找不到本機詞條", errors.getvalue())

    def test_cli_can_disable_fuzzy_candidates(self):
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["lookup", "--json", "embeding"]), 0)
        self.assertEqual(json.loads(output.getvalue())["explanations"][0]["match"], "shipped_canonical_fuzzy")
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["lookup", "--no-fuzzy", "embeding"]), 1)
        self.assertIn("找不到本機詞條", errors.getvalue())

    def _write_ecdict_csv(self):
        path = Path(self.temp_data_home.name) / "ecdict.csv"
        path.write_text(
            "word,phonetic,definition,translation,pos\n"
            "embedding,,,一般詞典的向量條目,n\n"
            "zorb,zoːb,,虛構的一般詞典詞條,n\n",
            encoding="utf-8",
        )
        return path

    def test_explicit_ecdict_import_is_fallback_only_and_explainable(self):
        output, errors = StringIO(), StringIO()
        csv_path = self._write_ecdict_csv()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["import-ecdict", str(csv_path)]), 0)
        self.assertIn("已匯入 2 個", output.getvalue())
        self.assertEqual(cli.main(["validate-data"]), 0)
        self.assertEqual(lookup("embedding")[0]["provenance"]["kind"], "legacy")
        fallback = lookup("zorb")[0]
        self.assertEqual(fallback["source_layer"], "ECDICT 一般詞典 fallback")
        self.assertEqual(explanation := core.explain_lookup("zorb"), [{
            "term": "zorb",
            "rank": 1,
            "match": "ecdict_generic_fallback",
            "provenance": {"kind": "sourced", "message": "sourced；來源紀錄，不等同正確性", "source_url": "https://github.com/skywind3000/ecdict"},
        }])
        self.assertEqual(lookup("zorb", allow_fallback=False), [])
        output.seek(0)
        output.truncate(0)
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["lookup", "--no-fallback", "zorb"]), 1)
        self.assertIn("找不到本機詞條", errors.getvalue())

    def test_ecdict_import_rejects_an_invalid_schema(self):
        path = Path(self.temp_data_home.name) / "bad-ecdict.csv"
        path.write_text("term,meaning\nzorb,錯誤\n", encoding="utf-8")
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["import-ecdict", str(path)]), 2)
        self.assertIn("必須包含 word 與 translation", errors.getvalue())

    def test_sdcv_is_explicit_isolated_and_never_part_of_ranked_lookup(self):
        dictionary_root = Path(self.temp_data_home.name) / "stardict"
        (dictionary_root / "dic").mkdir(parents=True)
        completed = __import__("subprocess").CompletedProcess(
            args=[], returncode=0,
            stdout='[{"dict":"fixture","word":"zorb","definition":"\\n虛構詞條"}]', stderr="",
        )
        with patch.object(sdcv.shutil, "which", return_value="/usr/bin/sdcv"), patch.object(sdcv.subprocess, "run", return_value=completed) as run:
            entries = sdcv.lookup("zorb", dictionary_root)
        self.assertEqual(entries[0]["term"], "zorb")
        self.assertEqual(entries[0]["source_layer"], "sdcv 明示本機 StarDict")
        self.assertEqual(entries[0]["provenance"]["kind"], "local_external")
        self.assertEqual(lookup("zorb"), [])
        command = run.call_args.args[0]
        self.assertIn("--only-data-dir", command)
        self.assertIn("--exact-search", command)
        self.assertEqual(command[-2], "--")
        self.assertEqual(command[-1], "zorb")
        self.assertEqual(run.call_args.kwargs["env"]["SDCV_HISTSIZE"], "0")
        self.assertNotIn("XDG_DATA_HOME", run.call_args.kwargs["env"])

    def test_lookup_sdcv_cli_requires_a_selected_dictionary_path(self):
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["lookup-sdcv", "--data-dir", str(Path(self.temp_data_home.name) / "missing"), "zorb"]), 2)
        self.assertIn("包含 dic/", errors.getvalue())

    def test_cli_exact_mode_disables_inflection_and_fuzzy_candidates(self):
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["lookup", "--exact", "embedding"]), 0)
        self.assertIn("embedding", output.getvalue())
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["lookup", "--exact", "embeddings"]), 1)
        self.assertIn("找不到本機詞條", errors.getvalue())
        errors.seek(0)
        errors.truncate(0)
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["lookup", "--exact", "embeding"]), 1)
        self.assertIn("找不到本機詞條", errors.getvalue())

    def test_curated_only_excludes_private_overlay_and_generic_fallback(self):
        save_user_entries([{"term": "canary", "aliases": [], "domain": "測試", "definition": "私人覆寫", "status": "私人"}])
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["lookup", "--json", "--curated-only", "canary"]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["results"][0]["senses"][0]["definition"], "早期或實驗性發布通道；在版本名稱與套件標籤中通常保留 canary。")
        self.assertEqual(payload["explanations"][0]["match"], "shipped_canonical_exact")
        self.assertEqual(lookup("zorb", include_overlay=False, allow_fallback=False), [])

    def test_cli_rejects_conflicting_lookup_match_modes(self):
        errors = StringIO()
        with redirect_stderr(errors):
            with self.assertRaises(SystemExit) as raised:
                cli.main(["lookup", "--exact", "--no-fuzzy", "embedding"])
        self.assertEqual(raised.exception.code, 2)

    def test_invalid_query_returns_two_and_writes_stderr(self):
        output, errors = StringIO(), StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["this input contains too many words for a term"]), 2)
        self.assertEqual(output.getvalue(), "")
        self.assertIn("輸入不符合範圍", errors.getvalue())

    def test_json_lookup_has_stable_local_shape(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["lookup", "--json", "canary"]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual(payload["results"][0]["term"], "canary")
        self.assertEqual(len(payload["results"][0]["senses"]), 3)
        self.assertEqual(payload["results"][0]["provenance"], {"version": 1, "kind": "legacy"})
        self.assertEqual(payload["results"][0]["trust_level"], "legacy")
        self.assertEqual(payload["explanations"][0]["match"], "shipped_canonical_exact")
        self.assertEqual(payload["explanations"][0]["provenance"]["kind"], "legacy")

    def test_json_find_has_stable_local_shape(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["find", "--json", "roll"]), 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload["schema_version"], 2)
        self.assertEqual([entry["term"] for entry in payload["results"]], ["roll forward", "rollback", "rollover"])

    def test_data_validation_reports_schema_duplicates_and_context_errors(self):
        entries = [
            {"schema_version": 99, "term": "duplicate", "aliases": ["same"], "status": "x", "senses": [{"domain": "x", "definition": "x", "context_triggers": [], "context_required": False}]},
            {"schema_version": 2, "term": "other", "aliases": ["same"], "status": "", "senses": [{"domain": "", "definition": "x", "context_triggers": [], "context_required": True}]},
        ]
        errors = validate_entries(entries, "test")
        self.assertTrue(any("invalid schema_version" in error for error in errors))
        self.assertTrue(any("duplicate canonical term or alias" in error for error in errors))
        self.assertTrue(any("empty required field status" in error for error in errors))
        self.assertTrue(any("context-required record needs context_triggers" in error for error in errors))

    def test_abbreviation_schema_requires_all_structured_fields(self):
        entry = self._curated_entry({"version": 1, "kind": "sourced", "source_url": "https://example.com/term"})
        entry["abbreviation"] = {"short": "FT", "full_name": "Future Term"}
        self.assertTrue(any("invalid abbreviation record" in error for error in validate_entries([entry], "seed")))

    def test_abbreviation_identifiers_participate_in_duplicate_validation(self):
        first = self._curated_entry({"version": 1, "kind": "sourced", "source_url": "https://example.com/first"})
        first["abbreviation"] = {
            "short": "FT",
            "full_name": "Future Term",
            "display_name": "FT",
            "kind": "test",
            "context_required": False,
        }
        second = self._curated_entry({"version": 1, "kind": "sourced", "source_url": "https://example.com/second"})
        second["term"] = "another future term"
        second["aliases"] = ["FT"]
        self.assertTrue(any("duplicate canonical term or alias" in error for error in validate_entries([first, second], "seed")))

    def test_validate_data_command_accepts_shipped_schema(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["validate-data"]), 0)
        self.assertIn("資料驗證通過", output.getvalue())

    def test_shipped_seed_entries_are_explicitly_legacy(self):
        legacy_terms = {"canary", "embedding", "pull request"}
        entries = {entry["term"]: entry for entry in seed_entries()}
        for term in legacy_terms:
            self.assertEqual(entries[term]["provenance"], {"version": 1, "kind": "legacy"})
            self.assertEqual(entries[term]["trust_level"], "legacy")

    def test_curated_expansion_terms_are_sourced_and_lookupable(self):
        expected_sources = {
            "backpressure": "https://www.reactive-streams.org/",
            "feature flag": "https://martinfowler.com/articles/feature-toggles.html",
            "circuit breaker": "https://martinfowler.com/bliki/CircuitBreaker.html",
            "eventual consistency": "https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf",
        }
        entries = {entry["term"]: entry for entry in seed_entries()}
        for term, source_url in expected_sources.items():
            self.assertEqual(entries[term]["provenance"], {"version": 1, "kind": "sourced", "source_url": source_url})
            self.assertEqual(entries[term]["trust_level"], "maintainer_verified")
            self.assertEqual(lookup(term)[0]["term"], term)

    def test_gen_ai_extension_batch_is_curated_and_context_safe(self):
        entries = {entry["term"]: entry for entry in seed_entries()}
        source_url = "https://github.com/danielskry/gen-ai-glossary/blob/beee4ed4f0a81f53a1c367de63740cfcac729ba8/data/terms.json"
        self.assertEqual(entries["vector database"]["provenance"]["source_url"], source_url)
        self.assertTrue(entries["prompt"]["senses"][0]["context_required"])
        self.assertTrue(entries["agent memory"]["senses"][0]["context_required"])
        self.assertEqual(lookup("vector store")[0]["term"], "vector database")

    def test_gen_ai_locked_source_alias_expansion_is_lookupable(self):
        expected = {
            "token window": "token window",
            "AI hallucination": "AI hallucination",
            "agentic AI": "autonomous agent",
            "prompting techniques": "prompt",
        }
        for alias, term in expected.items():
            self.assertEqual(lookup(alias)[0]["term"], term)
        entries = {entry["term"]: entry for entry in seed_entries()}
        for term in ("autonomous agent", "token window", "AI hallucination"):
            self.assertEqual(entries[term]["provenance"]["source_url"], "https://github.com/danielskry/gen-ai-glossary/blob/beee4ed4f0a81f53a1c367de63740cfcac729ba8/data/terms.json")

    def test_historical_overlay_remains_readable_without_rewrite(self):
        save_user_entries([{"term": "historic term", "aliases": [], "domain": "測試", "definition": "舊資料", "status": "私人"}])
        before = overlay_path().read_text(encoding="utf-8")
        entry = user_entries()[0]
        self.assertEqual(entry["term"], "historic term")
        self.assertEqual(entry["provenance"], {"version": 1, "kind": "private"})
        self.assertEqual(entry["trust_level"], "community")
        self.assertEqual(overlay_path().read_text(encoding="utf-8"), before)

    def _curated_entry(self, provenance):
        return {"schema_version": 2, "term": "future term", "aliases": [], "status": "常用", "provenance": provenance, "trust_level": "maintainer_verified", "attribution": {"kind": "upgrade", "upgraded_by": "test maintainer", "evidence": "https://example.com/review", "date": "2026-07-14"}, "senses": [{"domain": "測試", "definition": "未來詞條", "context_triggers": [], "context_required": False}]}

    def test_trust_level_schema_rejects_missing_or_unknown_values(self):
        missing = self._curated_entry({"version": 1, "kind": "sourced", "source_url": "https://example.com/term"})
        missing.pop("trust_level")
        unknown = self._curated_entry({"version": 1, "kind": "sourced", "source_url": "https://example.com/term"})
        unknown["trust_level"] = "unreviewed"
        errors = validate_entries([missing, unknown], "seed")
        self.assertEqual(sum("invalid trust_level" in error for error in errors), 2)

    def test_public_trust_upgrades_require_attribution_except_grandfathered_seed(self):
        entry = self._curated_entry({"version": 1, "kind": "sourced", "source_url": "https://example.com/term"})
        entry.pop("attribution")
        self.assertTrue(any("trust upgrade requires attribution" in error for error in validate_entries([entry], "seed")))

        grandfathered = self._curated_entry({"version": 1, "kind": "sourced", "source_url": "https://example.com/term"})
        grandfathered.update({
            "term": "sdcv",
            "attribution": {"kind": "grandfathered", "note": "原始 seed,無正式升級紀錄"},
        })
        self.assertEqual(validate_entries([grandfathered], "seed"), [])

    def test_private_community_overlay_does_not_require_public_upgrade_attribution(self):
        entry = self._curated_entry({"version": 1, "kind": "private"})
        entry["trust_level"] = "community"
        entry.pop("attribution")
        self.assertEqual(validate_entries([entry], "overlay", allow_private=True), [])

    def test_sourced_provenance_requires_valid_https_url(self):
        errors = validate_entries([self._curated_entry({"version": 1, "kind": "sourced", "source_url": "http://example.com"})], "seed")
        self.assertTrue(any("valid HTTPS source_url" in error for error in errors))

    def test_future_curated_entry_without_provenance_fails_closed(self):
        entry = self._curated_entry({})
        entry.pop("provenance")
        errors = validate_entries([entry], "seed")
        self.assertTrue(any("invalid provenance" in error for error in errors))

    def test_no_public_source_provenance_requires_reason(self):
        errors = validate_entries([self._curated_entry({"version": 1, "kind": "no_public_source", "reason": ""})], "seed")
        self.assertTrue(any("no_public_source provenance requires a reason" in error for error in errors))

    def test_valid_curated_provenance_records_pass(self):
        sourced = self._curated_entry({"version": 1, "kind": "sourced", "source_url": "https://example.com/term"})
        no_public_source = self._curated_entry({"version": 1, "kind": "no_public_source", "reason": "團隊內部名稱"})
        no_public_source["term"] = "another future term"
        self.assertEqual(validate_entries([sourced, no_public_source], "seed"), [])

    def test_provenance_summaries_distinguish_all_supported_kinds(self):
        summaries = [
            core.provenance_summary({"provenance": {"version": 1, "kind": "legacy"}}),
            core.provenance_summary({"provenance": {"version": 1, "kind": "private"}}),
            core.provenance_summary({"provenance": {"version": 1, "kind": "sourced", "source_url": "https://example.com"}}),
            core.provenance_summary({"provenance": {"version": 1, "kind": "no_public_source", "reason": "內部名稱"}}),
        ]
        self.assertEqual([summary["kind"] for summary in summaries], ["legacy", "private", "sourced", "no_public_source"])
        self.assertNotIn("source_url", summaries[1])

    def test_text_explain_shows_deterministic_match_reason(self):
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["lookup", "--explain", "provenance"]), 0)
        self.assertIn("來源紀錄：legacy", output.getvalue())
        self.assertIn("shipped_canonical_exact", output.getvalue())

    def test_private_overlay_json_explanation_stays_private(self):
        save_user_entries([{"term": "private term", "aliases": [], "domain": "測試", "definition": "私人", "status": "私人"}])
        output = StringIO()
        with redirect_stdout(output):
            self.assertEqual(cli.main(["lookup", "--json", "private term"]), 0)
        explanation = json.loads(output.getvalue())["explanations"][0]["provenance"]
        self.assertEqual(explanation["kind"], "private")
        self.assertNotIn("source_url", explanation)

    def test_interactive_add_uses_temporary_overlay(self):
        answers = ["local term", "", "測試", "僅供測試", "團隊用語", ""]
        with patch("builtins.input", side_effect=answers), redirect_stdout(StringIO()):
            self.assertEqual(cli.main(["add"]), 0)
        self.assertTrue(overlay_path().is_relative_to(Path(self.temp_data_home.name)))
        self.assertEqual(user_entries()[0]["term"], "local term")
        self.assertFalse(user_entries()[0]["shareable"])
        self.assertEqual(raw_user_entries()[0]["provenance"], {"version": 1, "kind": "private"})
        self.assertEqual(raw_user_entries()[0]["trust_level"], "community")

    def test_interactive_add_rejects_private_canonical_or_alias_conflicts_without_writing(self):
        save_user_entries([{"term": "existing term", "aliases": ["reserved name"], "domain": "測試", "definition": "既有詞條", "status": "私人"}])
        before = overlay_path().read_text(encoding="utf-8")
        answers = ["Reserved Name", "", "測試", "衝突詞條", "團隊用語", ""]
        output, errors = StringIO(), StringIO()
        with patch("builtins.input", side_effect=answers), redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["add"]), 2)
        self.assertIn("私人詞條名稱衝突", errors.getvalue())
        self.assertIn("未寫入任何資料", errors.getvalue())
        self.assertEqual(overlay_path().read_text(encoding="utf-8"), before)

    def test_private_add_explicitly_prefills_a_scan_term_and_can_define_an_abbreviation(self):
        answers = ["", "測試", "僅供測試", "團隊用語", ""]
        with patch("builtins.input", side_effect=answers), redirect_stdout(StringIO()):
            self.assertEqual(cli.main([
                "private", "add", "--term", "team release", "--abbreviation", "TR",
                "--full-name", "Team Release", "--abbreviation-kind", "team_release",
            ]), 0)
        entry = user_entries()[0]
        self.assertEqual(entry["term"], "team release")
        self.assertEqual(entry["abbreviation"], {
            "short": "TR",
            "full_name": "Team Release",
            "display_name": "TR",
            "kind": "team_release",
            "context_required": False,
        })

    def test_private_add_rejects_incomplete_abbreviation_without_writing(self):
        errors = StringIO()
        with redirect_stderr(errors):
            self.assertEqual(cli.main(["private", "add", "--term", "team release", "--abbreviation", "TR"]), 2)
        self.assertIn("同時提供", errors.getvalue())
        self.assertFalse(overlay_path().exists())

    def test_cancelled_add_returns_130_without_writing_overlay(self):
        output, errors = StringIO(), StringIO()
        with patch("builtins.input", side_effect=EOFError), redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(cli.main(["add"]), 130)
        self.assertIn("已取消", errors.getvalue())
        self.assertFalse(overlay_path().exists())

    def test_production_files_reject_networking_and_limit_subprocess_to_sdcv_adapter(self):
        package = Path(__file__).parents[1] / "englex"
        forbidden_networking = ("socket", "urllib", "http.client", "requests", "asyncio")
        for source in package.glob("*.py"):
            content = source.read_text(encoding="utf-8")
            self.assertFalse(
                any("import " + name in content or "from " + name in content for name in forbidden_networking),
                f"forbidden networking import in {source.name}",
            )
            if source.name != "sdcv.py":
                self.assertNotIn("import subprocess", content, f"unexpected subprocess import in {source.name}")


if __name__ == "__main__":
    unittest.main()
