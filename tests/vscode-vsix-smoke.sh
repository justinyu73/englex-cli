#!/usr/bin/env sh
set -eu

artifact_root="$(mktemp -d)"
npm_root="$(mktemp -d)"
extension_id="englex-local.englex-selection"
installed=0

cleanup() {
  status=$?
  if [ "$installed" -eq 1 ]; then
    code --uninstall-extension "$extension_id" >/dev/null 2>&1 || true
  fi
  rm -rf "$artifact_root" "$npm_root"
  trap - EXIT
  exit "$status"
}
trap cleanup EXIT

grep -F 'npx --yes @vscode/vsce package' vscode-extension/README.md >/dev/null
grep -F 'code --install-extension "$work_dir/englex-selection.vsix"' vscode-extension/README.md >/dev/null

existing="$(code --list-extensions --show-versions | grep -i "^$extension_id@" || true)"
if [ -n "$existing" ]; then
  printf '%s\n' "Refusing to replace an existing $extension_id installation." >&2
  exit 3
fi

(
  cd vscode-extension
  npm_config_cache="$npm_root" npx --yes @vscode/vsce package --out "$artifact_root/englex-selection.vsix"
)

vsix="$artifact_root/englex-selection.vsix"
test -s "$vsix"
code --install-extension "$vsix"
installed=1
code --list-extensions | grep -Fx "$extension_id" >/dev/null
code --uninstall-extension "$extension_id"
installed=0
