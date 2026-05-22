const fs = require("fs");
const path = require("path");
const vscode = require("vscode");

function activate(context) {
  const provider = new ModulesProvider();
  context.subscriptions.push(
    vscode.window.registerTreeDataProvider("dynamicSs13Modules.modules", provider),
    vscode.commands.registerCommand("dynamicSs13Modules.refresh", () => provider.refresh()),
    vscode.commands.registerCommand("dynamicSs13Modules.openIndex", openIndex),
    vscode.commands.registerCommand("dynamicSs13Modules.openMaterializedFile", openMaterializedFile),
    vscode.commands.registerCommand("dynamicSs13Modules.explainCurrentFile", explainCurrentFile),
    vscode.languages.registerCodeLensProvider({ scheme: "file" }, new InteractionCodeLensProvider()),
    vscode.languages.registerHoverProvider({ scheme: "file" }, new InteractionHoverProvider())
  );
}

function deactivate() {}

class ModulesProvider {
  constructor() {
    this._onDidChangeTreeData = new vscode.EventEmitter();
    this.onDidChangeTreeData = this._onDidChangeTreeData.event;
  }

  refresh() {
    this._onDidChangeTreeData.fire();
  }

  getTreeItem(element) {
    return element;
  }

  getChildren() {
    const index = readIndex();
    if (!index) {
      return [new vscode.TreeItem("Run dynamic-modules prepare", vscode.TreeItemCollapsibleState.None)];
    }
    return (index.load_order || []).map((id) => {
      const module = index.modules?.[id] || {};
      const item = new vscode.TreeItem(`${id} ${module.version || ""}`, vscode.TreeItemCollapsibleState.None);
      item.description = module.name || "";
      item.tooltip = `${module.name || id}\n${module.root || ""}`;
      return item;
    });
  }
}

class InteractionCodeLensProvider {
  provideCodeLenses(document) {
    const interactions = interactionsForDocument(document);
    if (!interactions.length) {
      return [];
    }
    const lenses = [
      new vscode.CodeLens(new vscode.Range(0, 0, 0, 0), {
        title: `Dynamic Modules: ${interactions.length} interaction${interactions.length === 1 ? "" : "s"}`,
        command: "dynamicSs13Modules.explainCurrentFile"
      })
    ];
    for (const interaction of interactions) {
      if (interaction.kind === "patch" && Number.isInteger(interaction.anchor_line)) {
        const line = Math.max(0, interaction.anchor_line - 1);
        lenses.push(new vscode.CodeLens(new vscode.Range(line, 0, line, 0), {
          title: `${interaction.module}:${interaction.id} ${interaction.mode}`,
          command: "dynamicSs13Modules.explainCurrentFile"
        }));
      }
    }
    return lenses;
  }
}

class InteractionHoverProvider {
  provideHover(document) {
    const interactions = interactionsForDocument(document);
    if (!interactions.length) {
      return undefined;
    }
    const lines = ["**Dynamic Modules interactions**", ""];
    for (const item of interactions) {
      if (item.kind === "patch") {
        lines.push(`- patch \`${item.module}:${item.id}\` at line ${item.anchor_line}`);
      } else if (item.kind === "hook") {
        lines.push(`- hook \`${item.module}:${item.id}\` targets \`${item.target}\``);
      }
    }
    return new vscode.Hover(new vscode.MarkdownString(lines.join("\n")));
  }
}

function explainCurrentFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showInformationMessage("No active editor.");
    return;
  }
  const interactions = interactionsForDocument(editor.document);
  if (!interactions.length) {
    vscode.window.showInformationMessage("No Dynamic Modules interactions recorded for this file.");
    return;
  }
  const panel = vscode.window.createOutputChannel("Dynamic Modules");
  panel.clear();
  panel.appendLine(`Interactions for ${editor.document.fileName}`);
  for (const item of interactions) {
    panel.appendLine(JSON.stringify(item, null, 2));
  }
  panel.show();
}

function openIndex() {
  const indexPath = findIndexPath();
  if (!indexPath || !fs.existsSync(indexPath)) {
    vscode.window.showWarningMessage("No Dynamic Modules index found. Run dynamic-modules prepare.");
    return;
  }
  vscode.workspace.openTextDocument(indexPath).then((doc) => vscode.window.showTextDocument(doc));
}

function openMaterializedFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showInformationMessage("No active editor.");
    return;
  }
  const index = readIndex();
  if (!index) {
    vscode.window.showWarningMessage("No Dynamic Modules index found. Run dynamic-modules prepare.");
    return;
  }
  const patched = interactionsForDocument(editor.document).filter((item) => item.kind === "patch" && item.output_file);
  if (!patched.length) {
    vscode.window.showInformationMessage("No materialized patch overlay recorded for this file.");
    return;
  }
  const buildDir = path.join(index.host_root, index.build_dir || ".dynamic_modules_build");
  const outputPath = path.join(buildDir, patched[patched.length - 1].output_file);
  vscode.workspace.openTextDocument(outputPath).then((doc) => vscode.window.showTextDocument(doc));
}

function interactionsForDocument(document) {
  const index = readIndex();
  if (!index) {
    return [];
  }
  const root = index.host_root || workspaceRoot();
  const rel = path.relative(root, document.fileName).replace(/\\/g, "/");
  return index.files?.[rel] || [];
}

function readIndex() {
  const indexPath = findIndexPath();
  if (!indexPath || !fs.existsSync(indexPath)) {
    return null;
  }
  try {
    return JSON.parse(fs.readFileSync(indexPath, "utf8"));
  } catch (error) {
    vscode.window.showWarningMessage(`Could not read Dynamic Modules index: ${error.message}`);
    return null;
  }
}

function findIndexPath() {
  const root = workspaceRoot();
  if (!root) {
    return null;
  }
  const configured = vscode.workspace.getConfiguration("dynamicSs13Modules").get("indexPath");
  return path.join(root, configured || ".dynamic_modules_build/index.json");
}

function workspaceRoot() {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || !folders.length) {
    return null;
  }
  return folders[0].uri.fsPath;
}

module.exports = { activate, deactivate };
