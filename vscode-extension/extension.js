"use strict";

const { execFile } = require("child_process");

let outputChannel;
let terminalLinkProvider;

function runScan(executable, selectedText) {
  return new Promise((resolve, reject) => {
    execFile(executable, ["scan", "--json", selectedText], {
      encoding: "utf8",
      maxBuffer: 1024 * 1024,
      windowsHide: true,
    }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error((stderr || error.message).trim()));
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (parseError) {
        reject(new Error(`Englex returned invalid JSON: ${parseError.message}`));
      }
    });
  });
}

function runWishlistAdd(executable, term) {
  return new Promise((resolve, reject) => {
    execFile(executable, ["wishlist", "add", term], {
      encoding: "utf8",
      maxBuffer: 1024 * 1024,
      windowsHide: true,
    }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error((stderr || error.message).trim()));
        return;
      }
      resolve(stdout);
    });
  });
}

function runWishlistList(executable) {
  return new Promise((resolve, reject) => {
    execFile(executable, ["wishlist", "list", "--json"], {
      encoding: "utf8",
      maxBuffer: 1024 * 1024,
      windowsHide: true,
    }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error((stderr || error.message).trim()));
        return;
      }
      try {
        resolve(JSON.parse(stdout));
      } catch (parseError) {
        reject(new Error(`Englex returned invalid JSON: ${parseError.message}`));
      }
    });
  });
}

// Maintainer-only dev-time batch: runs the repo-checkout tool that calls an
// online model with the maintainer's own key. Never part of the lookup runtime.
function runWishlistAuto(repoPath) {
  return new Promise((resolve, reject) => {
    execFile("python3", ["tools/wishlist_draft.py", "auto"], {
      cwd: repoPath,
      encoding: "utf8",
      maxBuffer: 1024 * 1024,
      windowsHide: true,
    }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error((stderr || stdout || error.message).trim()));
        return;
      }
      resolve(stdout);
    });
  });
}

// The installed englex reads its seed via importlib.resources, so a merged
// batch only takes effect after reinstalling from the checkout. PEP 668
// externally-managed systems (Ubuntu 24.04+) reject plain pip installs; retry
// once with --break-system-packages, which with --user only touches ~/.local.
function runReinstall(repoPath) {
  const pipInstall = (extraArgs) => new Promise((resolve, reject) => {
    execFile("python3", ["-m", "pip", "install", "--user", ...extraArgs, repoPath], {
      encoding: "utf8",
      maxBuffer: 1024 * 1024,
      windowsHide: true,
    }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error((stderr || error.message).trim()));
        return;
      }
      resolve(stdout);
    });
  });
  return pipInstall([]).catch((firstError) => {
    if (!firstError.message.includes("externally-managed-environment")) {
      throw firstError;
    }
    return pipInstall(["--break-system-packages"]);
  });
}

const TRUST_LABEL = {
  ai_drafted: "AI 草擬，未審定",
  community: "社群提供，未維護者審定",
  maintainer_verified: "維護者審定",
  legacy: "既有隨附，未回溯驗證",
};

function renderEntry(result) {
  const entry = result.entry;
  const senses = entry.senses || [];
  const abbreviation = entry.abbreviation
    ? `（縮寫 ${entry.abbreviation.short}＝${entry.abbreviation.full_name}）`
    : "";
  const trust = entry.trust_level
    ? ` · 信任等級：${entry.trust_level}${TRUST_LABEL[entry.trust_level] ? `（${TRUST_LABEL[entry.trust_level]}）` : ""}`
    : "";
  const lines = [`${entry.term}${abbreviation}${trust}`];
  const ranking = entry.context_ranking;
  const mostLikely = ranking && ranking.decision === "most_likely" && senses.length > 1
    ? ranking.most_likely_sense_number
    : null;
  if (mostLikely) {
    lines.push(`  最可能義項 ${mostLikely}（命中：${(ranking.matched_triggers || []).join(", ")}）`);
  }
  senses.forEach((sense, index) => {
    const mark = index + 1 === mostLikely ? "  ← 最可能" : "";
    lines.push(`  ${index + 1}. [${sense.domain}] ${sense.definition}${mark}`);
  });
  return lines.join("\n");
}

function render(payload) {
  if (!payload.results.length) {
    return "找不到已知工程術語。";
  }
  const blocks = payload.results.map(renderEntry);
  if (payload.unmatched.length) {
    blocks.push(`未命中：${payload.unmatched.map((item) => item.text).join(", ")}`);
  }
  return blocks.join("\n\n");
}

function isTermShape(text) {
  if (typeof text !== "string" || text.includes("\n") || text.includes("\r")) {
    return false;
  }
  const compact = text.trim().replace(/\s+/g, " ");
  if (!compact || compact.length > 80 || compact.split(" ").length > 5) {
    return false;
  }
  return !/[.!?。！？]/.test(compact);
}

async function explainSelection(vscode, runScanImplementation = runScan) {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.selection.isEmpty) {
    vscode.window.showWarningMessage("請先明示選取一行英文，再執行 Englex。 ");
    return;
  }
  const selectedText = editor.document.getText(editor.selection);
  return scanAndRender(vscode, selectedText, runScanImplementation);
}

async function lookupInput(vscode, runScanImplementation = runScan) {
  const input = await vscode.window.showInputBox({
    prompt: "輸入或貼上要查的工程術語",
    placeHolder: "例如 reconcile",
  });
  if (!input || !input.trim()) {
    return;
  }
  return scanAndRender(vscode, input, runScanImplementation);
}

async function scanAndRender(vscode, text, runScanImplementation) {
  const executable = vscode.workspace.getConfiguration("englex").get("executable", "englex");
  try {
    const payload = await runScanImplementation(executable, text);
    outputChannel = outputChannel || vscode.window.createOutputChannel("Englex Selection");
    outputChannel.clear();
    outputChannel.appendLine(render(payload));
    outputChannel.show(true);
    if (payload.results.length === 0 && isTermShape(text)) {
      const action = await vscode.window.showInformationMessage(
        `找不到「${text}」，加入 wishlist？`,
        "加入 wishlist",
      );
      if (action === "加入 wishlist") {
        try {
          await runWishlistAdd(executable, text);
          vscode.window.showInformationMessage("已加入 wishlist");
        } catch (error) {
          vscode.window.showErrorMessage(`Englex wishlist add failed: ${error.message}`);
        }
      }
    }
  } catch (error) {
    vscode.window.showErrorMessage(`Englex scan failed: ${error.message}`);
  }
}

let wishlistStatusItem;

function setWishlistStatusCount(pending) {
  if (!wishlistStatusItem) {
    return;
  }
  wishlistStatusItem.text = pending > 0 ? `$(sync) Englex 補批 (${pending})` : "$(sync) Englex 補批";
}

async function refreshWishlistStatus(vscode, runWishlistListImplementation = runWishlistList) {
  if (!wishlistStatusItem) {
    return;
  }
  try {
    const executable = vscode.workspace.getConfiguration("englex").get("executable", "englex");
    const payload = await runWishlistListImplementation(executable);
    const pending = payload && typeof payload.pending_new === "number" ? payload.pending_new : 0;
    setWishlistStatusCount(pending);
  } catch (error) {
    // 狀態列計數只是提示；取數失敗（例如 CLI 未安裝）不得影響擴充啟動。
  }
}

// Maintainer-only dev-time flow: 讀 wishlist 淨新詞 → 確認後跑
// tools/wishlist_draft.py auto（維護者金鑰、線上模型、ai_drafted 併入）→
// 併入成功才提示重新安裝讓新詞條生效。門檻、驗證與併入全在 Python 工具側。
async function translateWishlist(vscode, implementations = {}) {
  const impls = { runWishlistList, runWishlistAuto, runReinstall, ...implementations };
  const executable = vscode.workspace.getConfiguration("englex").get("executable", "englex");
  let payload;
  try {
    payload = await impls.runWishlistList(executable);
  } catch (error) {
    vscode.window.showErrorMessage(`Englex wishlist list failed: ${error.message}`);
    return;
  }
  const pending = typeof payload.pending_new === "number" ? payload.pending_new : 0;
  setWishlistStatusCount(pending);
  if (pending === 0) {
    vscode.window.showInformationMessage("wishlist 沒有淨新待翻詞。");
    return;
  }
  const repoPath = vscode.workspace.getConfiguration("englex").get("maintainerRepo", "");
  if (!repoPath) {
    vscode.window.showWarningMessage(
      `wishlist 有 ${pending} 個淨新待翻詞；翻譯補批是維護者功能，請先設定 englex.maintainerRepo 指向本機 englex-cli checkout。`,
    );
    return;
  }
  const confirm = await vscode.window.showInformationMessage(
    `以維護者金鑰呼叫線上模型，草擬 ${pending} 個 wishlist 詞並併入詞庫？(dev-time；查詢 runtime 維持離線)`,
    "觸發補批",
  );
  if (confirm !== "觸發補批") {
    return;
  }
  let output;
  try {
    output = await impls.runWishlistAuto(repoPath);
  } catch (error) {
    vscode.window.showErrorMessage(`Englex wishlist auto failed: ${error.message}`);
    return;
  }
  outputChannel = outputChannel || vscode.window.createOutputChannel("Englex Selection");
  outputChannel.clear();
  outputChannel.appendLine(output.trim());
  outputChannel.show(true);
  if (!output.includes("併入")) {
    return;
  }
  await refreshWishlistStatus(vscode, impls.runWishlistList);
  const reinstall = await vscode.window.showInformationMessage(
    `已併入詞庫。重新安裝 englex 讓新詞條生效？(python3 -m pip install --user ${repoPath})`,
    "重新安裝",
    "稍後",
  );
  if (reinstall !== "重新安裝") {
    return;
  }
  try {
    await impls.runReinstall(repoPath);
    vscode.window.showInformationMessage("已重新安裝 englex，新詞條已生效。");
  } catch (error) {
    vscode.window.showErrorMessage(`englex 重新安裝失敗: ${error.message}`);
  }
}

function createTerminalLinkProvider(vscode, runScanImplementation = runScan) {
  const linksByLine = new Map();

  return {
    provideTerminalLinks({ line }) {
      if (typeof line !== "string") {
        return [];
      }
      if (linksByLine.has(line)) {
        return linksByLine.get(line);
      }
      const request = (async () => {
        try {
          const executable = vscode.workspace.getConfiguration("englex").get("executable", "englex");
          const payload = await runScanImplementation(executable, line);
          return (payload.results || []).map((result) => {
            const link = new vscode.TerminalLink(
              result.start,
              result.end,
              renderEntry(result),
            );
            link.data = result.text;
            return link;
          });
        } catch (error) {
          return [];
        }
      })();
      const cachedRequest = request.then((links) => {
        linksByLine.set(line, links);
        return links;
      });
      linksByLine.set(line, cachedRequest);
      return cachedRequest;
    },
    handleTerminalLink(link) {
      return scanAndRender(vscode, link.data, runScanImplementation);
    },
    dispose() {
      linksByLine.clear();
    },
  };
}

function activate(context, vscodeImplementation, runScanImplementation = runScan, runWishlistListImplementation = runWishlistList) {
  const vscode = vscodeImplementation || require("vscode");
  const selectionCommand = vscode.commands.registerCommand(
    "englex.explainSelection",
    () => explainSelection(vscode, runScanImplementation),
  );
  const inputCommand = vscode.commands.registerCommand(
    "englex.lookupInput",
    () => lookupInput(vscode, runScanImplementation),
  );
  const translateCommand = vscode.commands.registerCommand(
    "englex.translateWishlist",
    () => translateWishlist(vscode),
  );
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left);
  statusBarItem.text = "$(book) Englex";
  statusBarItem.command = "englex.lookupInput";
  statusBarItem.tooltip = "查工程術語（貼上詞→Enter）";
  statusBarItem.show();
  wishlistStatusItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left);
  wishlistStatusItem.text = "$(sync) Englex 補批";
  wishlistStatusItem.command = "englex.translateWishlist";
  wishlistStatusItem.tooltip = "觸發 wishlist AI 翻譯補批（維護者 dev-time）；括號數字是淨新待翻詞數";
  wishlistStatusItem.show();
  terminalLinkProvider = createTerminalLinkProvider(vscode, runScanImplementation);
  const terminalLinkRegistration = vscode.window.registerTerminalLinkProvider(terminalLinkProvider);
  context.subscriptions.push(selectionCommand, inputCommand, translateCommand, statusBarItem, wishlistStatusItem, terminalLinkRegistration);
  return refreshWishlistStatus(vscode, runWishlistListImplementation);
}

function deactivate() {
  if (terminalLinkProvider) {
    terminalLinkProvider.dispose();
    terminalLinkProvider = undefined;
  }
  if (wishlistStatusItem) {
    wishlistStatusItem.dispose();
    wishlistStatusItem = undefined;
  }
  if (outputChannel) {
    outputChannel.dispose();
    outputChannel = undefined;
  }
}

module.exports = { activate, deactivate, explainSelection, isTermShape, lookupInput, render, runReinstall, runScan, runWishlistAdd, runWishlistAuto, runWishlistList, translateWishlist };
