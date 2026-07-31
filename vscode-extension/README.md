# Englex Selection extension

This dependency-free VS Code entry exposes two lookup commands and clickable terminal links. **Englex: Explain Selected Engineering Terms** reads only the active explicit selection. **Englex: Look Up Engineering Term** opens an input box (also available from the always-visible **$(book) Englex** status-bar button) for a term typed or pasted by you. Both commands call the local executable as `englex scan --json INPUT_TEXT` without a shell and render the same output channel.

The input-box entry does not automatically read the clipboard, terminal, editor, workspace, files, or any other source: it processes only text you personally type or paste into the input box. The selection entry reads only the explicit editor selection. In particular, neither entry reads the clipboard; pressing Ctrl+V yourself into the input box is user input, not extension clipboard access. After the scan, the text is discarded: it is not persisted, uploaded, or added to history. Configure `englex.executable` only when the desired local executable is not already on `PATH`.

The terminal-link provider scans VS Code terminal output one line at a time locally and marks only known engineering terms returned by the local Englex glossary as clickable links. The line is compared in memory only; it is not written to disk, uploaded, added to history, or read from the clipboard. Hover 即顯示定義，點擊則開啟完整 Englex 解釋面板。This has a larger read surface than an input box that sees only what you type, so users should decide for themselves whether to use the terminal integration. Clicking a link renders that term's normal Englex explanation in the **Englex Selection** output channel.

The input-box command is `englex.lookupInput` and uses `Ctrl+Alt+L` (`Cmd+Alt+L` on macOS). The selection command keeps `Ctrl+Alt+E` and its editor-context menu. The status-bar button is available after VS Code startup and has tooltip **查工程術語（貼上詞→Enter）**.

When either entry completely misses a term-shaped input (one line, at most five words and 80 characters), it asks **找不到「<文字>」，加入 wishlist？**. Only clicking **加入 wishlist** runs local `englex wishlist add <文字>` and then shows **已加入 wishlist**; longer sentence-like misses do not prompt.

**Englex: Translate Wishlist Batch (Maintainer)** (`englex.translateWishlist`, also the **$(sync) Englex 補批** status-bar button with a net-new count) is a maintainer-only dev-time trigger, not a lookup feature. It runs local `englex wishlist list --json`; when net-new terms exist and `englex.maintainerRepo` points at a local englex-cli checkout, an explicit confirmation runs `python3 tools/wishlist_draft.py auto` inside that checkout. That tool is the only network path here: it drafts `ai_drafted` entries with the maintainer's own API key (`.env` in the checkout, never committed), validates them, and appends to the checkout's glossary seed. After a successful merge the command offers to run `python3 -m pip install --user <repo>` (retrying once with `--break-system-packages` on PEP 668 externally-managed systems, which with `--user` only touches `~/.local`) so the installed CLI picks up the new entries; below the batch threshold the tool is a no-op and no reinstall is offered. With `englex.maintainerRepo` empty the command shows guidance only. The status-bar count is read from the local wishlist; this command never reads the clipboard, workspace, or files, and all lookup features stay fully offline regardless.

## Private `.vsix` package and local installation

This extension is not published to VS Code Marketplace. To create a private `.vsix`, run the standard packaging tool in a temporary npm cache from the repository root:

```bash
work_dir="$(mktemp -d)"
(
  cd vscode-extension
  npm_config_cache="$work_dir/npm-cache" npx --yes @vscode/vsce package --out "$work_dir/englex-selection.vsix"
)
code --install-extension "$work_dir/englex-selection.vsix"
code --list-extensions | grep -Fx englex-local.englex-selection
```

The `.vsix` remains at `$work_dir/englex-selection.vsix` for private transfer. The `code` command installs it only into the connected local/WSL VS Code server profile; it does not upload the extension or selected text. To remove it later, run `code --uninstall-extension englex-local.englex-selection`.

## WSL local development

After this change is checked out, use VS Code **File → Open Folder** to open the `vscode-extension/` subfolder in a **WSL: Ubuntu** window, then press `F5`. The checked-in `Run Englex Selection (WSL)` launch configuration opens an Extension Development Host and prepends the sibling checkout's `.venv/bin` to `PATH`; after `python3 -m venv ../.venv` and `../.venv/bin/python -m pip install ..`, the default `englex` executable therefore resolves without editing VS Code settings. Do not use `code --extensionDevelopmentPath`: the WSL Remote CLI does not support that flag.

In the Extension Development Host, invoke **Englex: Look Up Engineering Term** from the Command Palette, press `Ctrl+Alt+L`, or click the **Englex** status-bar button, then type or paste a term into the input box and press Enter. You can also create a text file, explicitly select one line, and invoke **Englex: Explain Selected Engineering Terms** from the editor context menu, Command Palette, or `Ctrl+Alt+E`. Both results appear in the **Englex Selection** output channel. The CLI remains the authority for the 200-character single-line input validation and all result semantics.
