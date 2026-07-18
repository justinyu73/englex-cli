#!/bin/sh
set -eu

python3 - <<'PY'
import json
from contextlib import redirect_stdout
from io import StringIO

from englex import cli


def scan_json(line):
    output = StringIO()
    with redirect_stdout(output):
        if cli.main(["scan", "--json", line]) != 0:
            raise SystemExit(f"JSON scan failed: {line}")
    return json.loads(output.getvalue())


def scan_terminal(line):
    output = StringIO()
    with redirect_stdout(output):
        if cli.main(["scan", line]) != 0:
            raise SystemExit(f"terminal scan failed: {line}")
    return output.getvalue()


release = scan_json("canary traffic rollout")
release_ranking = release["results"][0]["entry"]["context_ranking"]
if release_ranking["decision"] != "most_likely" or release_ranking["most_likely_sense_number"] != 2:
    raise SystemExit("sense A trigger line did not select sense 2")
if release_ranking["matched_triggers"] != ["traffic", "rollout"]:
    raise SystemExit("sense A trigger line did not retain matching triggers")
if "最可能義項：2（命中線索：traffic, rollout）" not in scan_terminal("canary traffic rollout"):
    raise SystemExit("terminal output did not display sense A ranking")

test = scan_json("canary test monitor")
test_ranking = test["results"][0]["entry"]["context_ranking"]
if test_ranking["decision"] != "most_likely" or test_ranking["most_likely_sense_number"] != 3:
    raise SystemExit("sense B trigger line did not select sense 3")
if test_ranking["matched_triggers"] != ["test", "monitor"]:
    raise SystemExit("sense B trigger line did not retain matching triggers")

undetermined = scan_json("canary unrelated")
entry = undetermined["results"][0]["entry"]
if entry["context_ranking"]["decision"] != "undetermined":
    raise SystemExit("zero-trigger line must remain undetermined")
if entry["context_ranking"]["most_likely_sense_number"] is not None:
    raise SystemExit("undetermined line must not select a sense")
if len(entry["senses"]) != 3:
    raise SystemExit("undetermined line must retain every sense")
terminal = scan_terminal("canary unrelated")
if "上下文判定：無法由上下文判定" not in terminal or "最可能義項：" in terminal:
    raise SystemExit("terminal output was not honest about undetermined context")

print("context-aware sense-ranking smoke passed: two unique winners and one undetermined line")
PY
