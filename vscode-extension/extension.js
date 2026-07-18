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

function activate(context, vscodeImplementation, runScanImplementation = runScan) {
  const vscode = vscodeImplementation || require("vscode");
  const selectionCommand = vscode.commands.registerCommand(
    "englex.explainSelection",
    () => explainSelection(vscode, runScanImplementation),
  );
  const inputCommand = vscode.commands.registerCommand(
    "englex.lookupInput",
    () => lookupInput(vscode, runScanImplementation),
  );
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left);
  statusBarItem.text = "$(book) Englex";
  statusBarItem.command = "englex.lookupInput";
  statusBarItem.tooltip = "查工程術語（貼上詞→Enter）";
  statusBarItem.show();
  terminalLinkProvider = createTerminalLinkProvider(vscode, runScanImplementation);
  const terminalLinkRegistration = vscode.window.registerTerminalLinkProvider(terminalLinkProvider);
  context.subscriptions.push(selectionCommand, inputCommand, statusBarItem, terminalLinkRegistration);
}

function deactivate() {
  if (terminalLinkProvider) {
    terminalLinkProvider.dispose();
    terminalLinkProvider = undefined;
  }
  if (outputChannel) {
    outputChannel.dispose();
    outputChannel = undefined;
  }
}

module.exports = { activate, deactivate, explainSelection, isTermShape, lookupInput, render, runScan, runWishlistAdd };
