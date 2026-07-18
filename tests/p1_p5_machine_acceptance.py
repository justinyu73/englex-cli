#!/usr/bin/env python3
"""Run the fixed P1-P5 local product simulation without external access."""

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
COMMANDS = [
    [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-v"],
    ["sh", "tests/smoke.sh"],
    ["sh", "tests/private-lifecycle-smoke.sh"],
    ["sh", "tests/install-smoke.sh"],
    ["node", "--check", "vscode-extension/extension.js"],
    ["node", "tests/vscode-extension-smoke.js"],
    [sys.executable, "-B", "-m", "englex", "validate-data"],
]


def main():
    for command in COMMANDS:
        completed = subprocess.run(command, cwd=ROOT, env=ENVIRONMENT)
        if completed.returncode:
            return completed.returncode
    print("P1-P5 machine acceptance simulation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
