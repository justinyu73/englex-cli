#!/usr/bin/env bash
# englex 一鍵發版（dev-time 維護者工具，不進 wheel）：
#   檢查 → tag → build（wheel/sdist/vsix）→ GitHub Release
#
# 用法：tools/release.sh <版本號> [-y]
#   版本號不帶 v，例如：tools/release.sh 0.7.1
#   -y / --yes  跳過互動確認
#
# 前置條件：已 gh auth login；版本號（englex/__init__.py 與
# vscode-extension/package.json）與 CHANGELOG 的 [x.y.z] 區塊已先定版並合進 main
# （例如 release/x.y.z PR）。本腳本會把這些當檢查項，不符合就 fail-closed。
set -euo pipefail

say() { printf '== %s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

VERSION="${1:-}"
ASSUME_YES=0
case "${2:-}" in
  -y|--yes) ASSUME_YES=1 ;;
  "") ;;
  *) die "未知參數：$2（用法：tools/release.sh <版本號> [-y]）" ;;
esac
[ -n "$VERSION" ] || die "用法：tools/release.sh <版本號> [-y]（版本號不帶 v，例如 0.7.1）"

for cmd in git gh python3 npx; do
  command -v "$cmd" >/dev/null 2>&1 || die "需要 $cmd 在 PATH 上"
done
[ -f pyproject.toml ] && [ -d englex ] && [ -d vscode-extension ] || die "請在 repo 根目錄執行"
gh auth status >/dev/null 2>&1 || die "gh 未登入（先 gh auth login）"

say "0/4 檢查：main 同步、工作樹乾淨、版本一致、tag 不存在"
git fetch origin main --quiet
[ "$(git branch --show-current)" = "main" ] || die "請先 git switch main"
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] || die "本地 main 與 origin/main 不一致（先 git pull）"
[ -z "$(git status --porcelain)" ] || die "工作樹不乾淨（commit 或 stash 後再來）"
py_ver="$(python3 -c "import re; print(re.search(r'__version__ = \"(.+?)\"', open('englex/__init__.py').read()).group(1))")"
[ "$py_ver" = "$VERSION" ] || die "englex/__init__.py 版本是 $py_ver，不是 $VERSION"
js_ver="$(python3 -c "import json; print(json.load(open('vscode-extension/package.json'))['version'])")"
[ "$js_ver" = "$VERSION" ] || die "vscode-extension/package.json 版本是 $js_ver，不是 $VERSION"
notes="$(awk -v v="$VERSION" '$0 ~ "^## \\[" v "\\]" {found=1; next} /^## \[/ && found {exit} found' CHANGELOG.md)"
[ -n "$notes" ] || die "CHANGELOG.md 找不到 [$VERSION] 區塊（先定版再發布）"
if git rev-parse -q --verify "refs/tags/v$VERSION" >/dev/null 2>&1; then
  die "本地已存在 tag v$VERSION"
fi
if git ls-remote --exit-code --tags origin "v$VERSION" >/dev/null 2>&1; then
  die "origin 已存在 tag v$VERSION"
fi

say "將發布 englex v$VERSION @ $(git rev-parse --short HEAD)（= origin/main）"
if [ "$ASSUME_YES" -eq 0 ]; then
  read -r -p "確認繼續？[y/N] " ans
  case "$ans" in y|Y) ;; *) die "已取消" ;; esac
fi

say "1/4 打 tag 並推送"
git tag -a "v$VERSION" -m "englex v$VERSION"
git push origin "v$VERSION"

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

say "2/4 建 wheel / sdist"
python3 -m venv "$work/build-tools"
"$work/build-tools/bin/python" -m pip install -q build
"$work/build-tools/bin/python" -m build --outdir "$work/dist" "$(pwd)" >/dev/null

say "3/4 建 vsix 並驗證三件交付物"
(
  cd vscode-extension
  npm_config_cache="$work/npm-cache" npx --yes @vscode/vsce package --out "$work/dist/englex-selection-$VERSION.vsix" >/dev/null
)
python3 - "$work/dist" "$VERSION" <<'PY'
import glob
import json
import os
import sys
import zipfile

dist, version = sys.argv[1], sys.argv[2]
wheel = glob.glob(os.path.join(dist, f"englex-{version}-py3-none-any.whl"))
sdist = glob.glob(os.path.join(dist, f"englex-{version}.tar.gz"))
vsix = os.path.join(dist, f"englex-selection-{version}.vsix")
missing = ([f"englex-{version}-py3-none-any.whl"] if not wheel else []) \
    + ([f"englex-{version}.tar.gz"] if not sdist else []) \
    + ([] if os.path.exists(vsix) else [os.path.basename(vsix)])
if missing:
    raise SystemExit(f"缺交付物：{missing}")
pkg = json.loads(zipfile.ZipFile(vsix).read("extension/package.json"))
if pkg["version"] != version:
    raise SystemExit(f"vsix 版本 {pkg['version']} 與 {version} 不一致")
print("交付物驗證 OK：", os.path.basename(wheel[0]), os.path.basename(sdist[0]), os.path.basename(vsix))
PY

say "4/4 建立 GitHub Release"
gh release create "v$VERSION" \
  "$work/dist/englex-$VERSION-py3-none-any.whl" \
  "$work/dist/englex-$VERSION.tar.gz" \
  "$work/dist/englex-selection-$VERSION.vsix" \
  --title "englex v$VERSION" \
  --notes "$notes"

say "完成：v$VERSION 已發布（交付物附在 GitHub Release，臨時建置目錄已自動清除）"
