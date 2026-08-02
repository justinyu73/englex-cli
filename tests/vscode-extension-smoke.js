"use strict";

const assert = require("assert");
const childProcess = require("child_process");
const fs = require("fs");
const path = require("path");

const originalExecFile = childProcess.execFile;
const wishlistAddCalls = [];
let execFileBehavior = null; // 測試中段可替換的 stub 行為
childProcess.execFile = (executable, args, options, callback) => {
  if (execFileBehavior) {
    execFileBehavior(executable, args, options, callback);
    return;
  }
  wishlistAddCalls.push({ executable, args, options });
  callback(null, "已加入本機 wishlist。\n", "");
};
const extension = require("../vscode-extension/extension");

async function main() {
  const extensionDir = path.join(__dirname, "..", "vscode-extension");
  const manifest = JSON.parse(fs.readFileSync(path.join(extensionDir, "package.json"), "utf8"));
  const launch = JSON.parse(fs.readFileSync(path.join(extensionDir, ".vscode", "launch.json"), "utf8"));
  const wslLaunch = launch.configurations.find((configuration) => configuration.name === "Run Englex Selection (WSL)");
  assert.deepStrictEqual(manifest.extensionKind, ["workspace"]);
  assert.ok(wslLaunch);
  assert.strictEqual(wslLaunch.type, "extensionHost");
  assert.strictEqual(wslLaunch.request, "launch");
  assert.deepStrictEqual(wslLaunch.args, ["--extensionDevelopmentPath=${workspaceFolder}"]);
  assert.strictEqual(wslLaunch.env.PATH, "${workspaceFolder}/../.venv/bin:${env:PATH}");

  const commandHandlers = new Map();
  const statusBarItems = [];
  const terminalLinkProviders = [];
  let rendered = "";
  let inputBoxOptions;
  let inputResponse = "reconcile";
  const informationMessages = [];
  const informationResponses = [];
  const warningMessages = [];
  let maintainerRepoValue = "";
  let clipboardAccessed = false;
  const vscode = {
    commands: {
      registerCommand(id, handler) {
        assert.ok(["englex.explainSelection", "englex.lookupInput", "englex.translateWishlist"].includes(id));
        commandHandlers.set(id, handler);
        return { dispose() {} };
      },
    },
    workspace: {
      getConfiguration(section) {
        assert.strictEqual(section, "englex");
        return { get: (key, fallback) => key === "executable" ? "englex-test" : key === "maintainerRepo" ? maintainerRepoValue : fallback };
      },
    },
    window: {
      activeTextEditor: {
        selection: { isEmpty: false },
        document: { getText: () => "canary deployment" },
      },
      createOutputChannel() {
        return {
          clear() {},
          appendLine(text) { rendered = text; },
          show() {},
          dispose() {},
        };
      },
      createStatusBarItem(alignment) {
        assert.strictEqual(alignment, 1);
        const item = {
          text: "",
          command: "",
          tooltip: "",
          show() { item.shown = true; },
          dispose() {},
        };
        statusBarItems.push(item);
        return item;
      },
      registerTerminalLinkProvider(provider) {
        terminalLinkProviders.push(provider);
        return { dispose() {} };
      },
      async showInputBox(options) {
        inputBoxOptions = options;
        return inputResponse;
      },
      async showInformationMessage(message, ...actions) {
        informationMessages.push({ message, actions });
        return informationResponses.length ? informationResponses.shift() : "加入 wishlist";
      },
      showWarningMessage(message, ...actions) {
        warningMessages.push({ message, actions });
        return undefined;
      },
      showErrorMessage(message) { throw new Error(message); },
    },
    TerminalLink: class {
      constructor(start, end, tooltip) {
        this.start = start;
        this.end = end;
        this.tooltip = tooltip;
      }
    },
    StatusBarAlignment: { Left: 1 },
    env: {
      get clipboard() {
        clipboardAccessed = true;
        throw new Error("clipboard must not be accessed");
      },
    },
  };
  const context = { subscriptions: [] };
  const scanCalls = [];
  await extension.activate(context, vscode, async (receivedExecutable, receivedText) => {
    scanCalls.push({ receivedExecutable, receivedText });
    if (receivedText === "unknownterm" || receivedText === "this is a very long sentence") {
      return { results: [], unmatched: [{ text: receivedText }] };
    }
    if (receivedText === "Use canary deployment") {
      return {
        results: [{
          start: 4,
          end: 10,
          text: "canary",
          match_type: "canonical",
          entry: {
            term: "canary",
            source_layer: "curated",
            trust_level: "legacy",
            senses: [{ domain: "發布／SRE", definition: "本機測試術語解釋。" }],
          },
        }],
        unmatched: [],
      };
    }
    if (receivedText === "hello world") {
      return { results: [], unmatched: [{ text: receivedText }] };
    }
    if (receivedText === "canary") {
      return {
        results: [{
          start: 0,
          end: 6,
          text: "canary",
          match_type: "canonical",
          entry: {
            term: "canary",
            source_layer: "curated",
            trust_level: "legacy",
            senses: [{ domain: "發布／SRE", definition: "本機測試術語解釋。" }],
          },
        }],
        unmatched: [],
      };
    }
    return {
      results: [{
        start: 0,
        end: receivedText.length,
        text: receivedText,
        match_type: "canonical",
        entry: {
          term: receivedText,
          source_layer: "curated",
          trust_level: "legacy",
          senses: [{ domain: "測試", definition: "工程術語的本機定義。" }],
        },
      }],
      unmatched: [],
    };
  }, async () => ({ enabled: true, terms: ["alpha", "beta", "gamma"], pending_new: 3 }));
  assert.ok(commandHandlers.has("englex.explainSelection"));
  assert.ok(commandHandlers.has("englex.lookupInput"));
  assert.ok(commandHandlers.has("englex.translateWishlist"));
  assert.strictEqual(statusBarItems.length, 2);
  assert.strictEqual(statusBarItems[0].text, "$(book) Englex");
  assert.strictEqual(statusBarItems[0].command, "englex.lookupInput");
  assert.strictEqual(statusBarItems[0].tooltip, "查工程術語（貼上詞→Enter）");
  assert.strictEqual(statusBarItems[0].shown, true);
  assert.strictEqual(statusBarItems[1].text, "$(sync) Englex 補批 (3)");
  assert.strictEqual(statusBarItems[1].command, "englex.translateWishlist");
  assert.strictEqual(statusBarItems[1].tooltip, "觸發 wishlist AI 翻譯補批（維護者 dev-time）；括號數字是淨新待翻詞數");
  assert.strictEqual(statusBarItems[1].shown, true);
  assert.strictEqual(terminalLinkProviders.length, 1);
  assert.strictEqual(context.subscriptions.length, 6);
  const terminalLinkProvider = terminalLinkProviders[0];

  let executable;
  let selectedText;
  await extension.explainSelection(vscode, async (receivedExecutable, receivedText) => {
    executable = receivedExecutable;
    selectedText = receivedText;
    return {
      results: [{
        start: 0,
        end: 17,
        text: "canary deployment",
        match_type: "canonical",
        entry: {
        term: "canary deployment",
        source_layer: "curated",
        trust_level: "legacy",
        senses: [{ domain: "發布／SRE", definition: "先給小部分流量觀察再擴大的漸進發布策略。" }],
      },
      }],
      unmatched: [],
    };
  });
  assert.strictEqual(executable, "englex-test");
  assert.strictEqual(selectedText, "canary deployment");
  assert.match(rendered, /canary deployment/);
  // the explanation itself must be rendered, not just the match line
  assert.match(rendered, /信任等級/);
  assert.match(rendered, /漸進發布策略/);

  await commandHandlers.get("englex.lookupInput")();
  assert.deepStrictEqual(scanCalls, [{ receivedExecutable: "englex-test", receivedText: "reconcile" }]);
  assert.deepStrictEqual(inputBoxOptions, {
    prompt: "輸入或貼上要查的工程術語",
    placeHolder: "例如 reconcile",
  });
  assert.match(rendered, /工程術語的本機定義/);
  assert.strictEqual(informationMessages.length, 0);
  assert.strictEqual(wishlistAddCalls.length, 0);

  inputResponse = "unknownterm";
  await commandHandlers.get("englex.lookupInput")();
  assert.deepStrictEqual(informationMessages.slice(-2), [
    { message: "找不到「unknownterm」，加入 wishlist？", actions: ["加入 wishlist"] },
    { message: "已加入 wishlist", actions: [] },
  ]);
  assert.strictEqual(wishlistAddCalls.length, 1);
  assert.strictEqual(wishlistAddCalls[0].executable, "englex-test");
  assert.deepStrictEqual(wishlistAddCalls[0].args, ["wishlist", "add", "unknownterm"]);

  inputResponse = "this is a very long sentence";
  const informationCountBeforeLongMiss = informationMessages.length;
  const wishlistAddCountBeforeLongMiss = wishlistAddCalls.length;
  await commandHandlers.get("englex.lookupInput")();
  assert.strictEqual(informationMessages.length, informationCountBeforeLongMiss);
  assert.strictEqual(wishlistAddCalls.length, wishlistAddCountBeforeLongMiss);

  inputResponse = "";
  await commandHandlers.get("englex.lookupInput")();
  assert.strictEqual(scanCalls.length, 3);

  const terminalLine = "Use canary deployment";
  const terminalScanCountBefore = scanCalls.length;
  const terminalLinks = await terminalLinkProvider.provideTerminalLinks({ line: terminalLine });
  // (a) A known term becomes a link with the exact scan span and matched text.
  assert.strictEqual(terminalLinks.length, 1);
  assert.deepStrictEqual(
    { start: terminalLinks[0].start, end: terminalLinks[0].end, data: terminalLinks[0].data },
    { start: 4, end: 10, data: "canary" },
  );
  assert.match(terminalLinks[0].tooltip, /本機測試術語解釋/);
  assert.match(terminalLinks[0].tooltip, /信任等級：legacy/);
  const scanCountAfterTooltip = scanCalls.length;
  assert.strictEqual(scanCountAfterTooltip, terminalScanCountBefore + 1);
  const emptyTerminalLinks = await terminalLinkProvider.provideTerminalLinks({ line: "hello world" });
  assert.deepStrictEqual(emptyTerminalLinks, []);
  // (b) The same line is served from the in-memory cache without another scan.
  const cachedTerminalLinks = await terminalLinkProvider.provideTerminalLinks({ line: terminalLine });
  assert.strictEqual(cachedTerminalLinks, terminalLinks);
  assert.strictEqual(scanCalls.length, scanCountAfterTooltip + 1);
  // (c) Clicking the link delegates to the existing scan-and-render path.
  await terminalLinkProvider.handleTerminalLink(terminalLinks[0]);
  assert.strictEqual(scanCalls[scanCalls.length - 1].receivedText, "canary");
  assert.match(rendered, /本機測試術語解釋/);

  // (d) No clipboard API access is allowed.
  assert.strictEqual(clipboardAccessed, false);
  // multi-sense: the most-likely sense is marked from context_ranking
  const multi = extension.render({
    results: [{
      start: 0, end: 6, text: "canary", match_type: "canonical",
      entry: {
        term: "canary", source_layer: "curated", trust_level: "legacy",
        context_ranking: { decision: "most_likely", most_likely_sense_number: 2, matched_triggers: ["traffic"] },
        senses: [
          { domain: "發布／SRE", definition: "早期或實驗性發布通道。" },
          { domain: "發布／SRE", definition: "以少量流量驗證新版本。" },
        ],
      },
    }],
    unmatched: [],
  });
  assert.match(multi, /最可能義項 2/);
  assert.match(multi, /← 最可能/);
  assert.match(extension.render({ results: [], unmatched: [] }), /找不到/);
  assert.strictEqual(typeof extension.runScan, "function");
  assert.strictEqual(typeof extension.activate, "function");
  assert.ok(vscode.window.activeTextEditor.document.getText);

  // --- englex.translateWishlist（維護者 dev-time 補批）---
  const wishlistAutoCalls = [];
  const reinstallCalls = [];
  const batchSpies = {
    runWishlistAuto: async (repoPath) => { wishlistAutoCalls.push(repoPath); return "unused"; },
    runReinstall: async (repoPath) => { reinstallCalls.push(repoPath); return "ok"; },
  };

  // (e) 有淨新詞但未設 maintainerRepo → 引導警告，不跑補批
  await extension.translateWishlist(vscode, {
    ...batchSpies,
    runWishlistList: async () => ({ enabled: true, terms: ["alpha", "beta", "gamma"], pending_new: 3 }),
  });
  assert.deepStrictEqual(warningMessages.slice(-1), [{
    message: "wishlist 有 3 個淨新待翻詞；翻譯補批是維護者功能，請先設定 englex.maintainerRepo 指向本機 englex-cli checkout。",
    actions: [],
  }]);
  assert.strictEqual(wishlistAutoCalls.length, 0);

  // (f) 無淨新詞 → 單純提示、狀態列數字即時歸零，不警告、不跑補批
  const infoCountBeforeZero = informationMessages.length;
  await extension.translateWishlist(vscode, {
    ...batchSpies,
    runWishlistList: async () => ({ enabled: true, terms: [], pending_new: 0 }),
  });
  assert.deepStrictEqual(informationMessages.slice(infoCountBeforeZero), [
    { message: "wishlist 沒有淨新待翻詞。", actions: [] },
  ]);
  assert.strictEqual(statusBarItems[1].text, "$(sync) Englex 補批");
  assert.strictEqual(wishlistAutoCalls.length, 0);

  // (g) 使用者不確認 → 不跑補批
  maintainerRepoValue = "/repo";
  informationResponses.push(undefined);
  await extension.translateWishlist(vscode, {
    ...batchSpies,
    runWishlistList: async () => ({ enabled: true, terms: ["a", "b", "c"], pending_new: 3 }),
  });
  assert.strictEqual(wishlistAutoCalls.length, 0);

  // (h) auto 輸出不含「併入」（防禦：零淨新 no-op 訊息）→ 顯示輸出，不出現重裝提示
  informationResponses.push("觸發補批");
  await extension.translateWishlist(vscode, {
    ...batchSpies,
    runWishlistList: async () => ({ enabled: true, terms: ["a", "b", "c"], pending_new: 3 }),
    runWishlistAuto: async (repoPath) => { wishlistAutoCalls.push(repoPath); return "沒有淨新待補詞，不觸發 AI 翻譯。\n"; },
  });
  assert.deepStrictEqual(wishlistAutoCalls, ["/repo"]);
  assert.match(rendered, /沒有淨新待補詞/);
  assert.ok(!informationMessages.some((entry) => entry.message.startsWith("已併入詞庫")));
  assert.strictEqual(reinstallCalls.length, 0);

  // (i) 併入成功（無門檻，≥1 淨新詞即跑，人為決定）→ 狀態列計數歸零、提示重裝、確認後以同一路徑重裝
  const listPayloads = [
    { enabled: true, terms: ["a", "b", "c"], pending_new: 3 },
    { enabled: true, terms: [], pending_new: 0 },
  ];
  informationResponses.push("觸發補批", "重新安裝");
  await extension.translateWishlist(vscode, {
    ...batchSpies,
    runWishlistList: async () => listPayloads.shift(),
    runWishlistAuto: async (repoPath) => { wishlistAutoCalls.push(repoPath); return "併入 3 條 ai_drafted（詞庫 entries → 157）；wishlist 清掉 3 個已收錄詞。\n"; },
  });
  assert.deepStrictEqual(wishlistAutoCalls, ["/repo", "/repo"]);
  assert.match(rendered, /併入 3 條 ai_drafted/);
  assert.strictEqual(statusBarItems[1].text, "$(sync) Englex 補批");
  assert.ok(informationMessages.some((entry) => entry.message.startsWith("已併入詞庫。重新安裝 englex 讓新詞條生效？(python3 -m pip install --user /repo)")));
  assert.deepStrictEqual(reinstallCalls, ["/repo"]);
  assert.deepStrictEqual(informationMessages.slice(-1), [
    { message: "已重新安裝 englex，新詞條已生效。", actions: [] },
  ]);

  // (j) PEP 668 externally-managed：runReinstall 以 --break-system-packages 重試一次；
  //     非 PEP 668 的失敗不重試
  const pipArgvs = [];
  let pipAttempts = 0;
  execFileBehavior = (file, args, options, callback) => {
    pipArgvs.push(args);
    pipAttempts += 1;
    if (pipAttempts === 1) {
      callback(new Error("Command failed"), "", "error: externally-managed-environment");
      return;
    }
    callback(null, "Successfully installed englex-0.7.1", "");
  };
  await extension.runReinstall("/repo");
  assert.deepStrictEqual(pipArgvs, [
    ["-m", "pip", "install", "--user", "/repo"],
    ["-m", "pip", "install", "--user", "--break-system-packages", "/repo"],
  ]);
  execFileBehavior = (file, args, options, callback) => {
    pipArgvs.push(args);
    callback(new Error("Command failed"), "", "ERROR: No matching distribution found");
  };
  await assert.rejects(() => extension.runReinstall("/repo"), /No matching distribution/);
  assert.strictEqual(pipArgvs.length, 3);
  execFileBehavior = null;

  extension.deactivate();
  childProcess.execFile = originalExecFile;
  console.log("vscode extension smoke passed");
}

main().catch((error) => {
  childProcess.execFile = originalExecFile;
  console.error(error.stack || error.message);
  process.exit(1);
});
