import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

// UI-4/UI-5 (Chase, 2026-09-29): one glossary. Users see "data set", "report", "view",
// "dashboard", "workstream", "organization", "unit of measure" -- never the engineering
// words below, and never a raw table name. Technical surfaces may say them.
const BANNED: [RegExp, string][] = [
  [/\bcanvas(es)?\b/i, "data set"],
  [/\breporting tables?\b/i, "data set"],
  [/\bdomains?\b/i, "data set"],
  [/\bsnapshots?\b/i, "data set"],
  [/\btenants?\b/i, "organization"],
  [/\buom\b/i, "unit of measure"],
  [/\b(reporting\.)?rpt_\w+/i, "the data set's name"],
];

// Surfaces that are allowed to be technical: the data model tab, the SQL workspace, the
// settings data source page, and any <details> disclosure labelled "for IT review".
const TECHNICAL_FILES = new Set([
  "components/SnapshotDataModelPanel.tsx",
  "components/DatabaseWorkspace.tsx",
  "components/DatabaseResultChart.tsx",
  "app/database/page.tsx",
  "components/DataSourceSettings.tsx",
]);

// Attributes that never reach a reader.
const CODE_ATTRIBUTES = new Set([
  "className", "href", "key", "id", "type", "name", "role", "htmlFor", "src",
  "target", "rel", "method", "value", "defaultValue", "form", "as",
]);

const SRC = join(__dirname);

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [path] : [];
  });
}

function isProse(text: string): boolean {
  // A lowercase token with no space is a key, a route or a comparison, not copy.
  return /\s/.test(text.trim()) || /^[A-Z]/.test(text.trim());
}

function readerText(node: ts.Node): string | null {
  const parent = node.parent;
  if (ts.isJsxText(node)) return node.text;
  if (!(ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)
    || ts.isTemplateHead(node) || ts.isTemplateMiddle(node) || ts.isTemplateTail(node))) return null;
  if (ts.isImportDeclaration(parent) || ts.isExportDeclaration(parent)) return null;
  if (ts.isPropertyAssignment(parent) && parent.name === node) return null;
  if (ts.isElementAccessExpression(parent)) return null;
  if (ts.isLiteralTypeNode(parent)) return null;
  const attr = ts.isJsxAttribute(parent) ? parent : null;
  if (attr) {
    const name = attr.name.getText();
    return CODE_ATTRIBUTES.has(name) || name.startsWith("data-") ? null : node.text;
  }
  if (ts.isCallExpression(parent) && parent.expression.getText().startsWith("console.")) return null;
  return isProse(node.text) ? node.text : null;
}

function violations(file: string): string[] {
  const source = ts.createSourceFile(file, readFileSync(file, "utf8"), ts.ScriptTarget.Latest, true);
  const found: string[] = [];
  const visit = (node: ts.Node) => {
    if (ts.isJsxElement(node) && node.openingElement.tagName.getText() === "details"
      && /for IT review/i.test(node.getText())) return;
    const text = readerText(node);
    if (text) {
      for (const [pattern, word] of BANNED) {
        const match = text.match(pattern);
        if (match) {
          const line = source.getLineAndCharacterOfPosition(node.getStart()).line + 1;
          found.push(`${relative(SRC, file)}:${line} "${match[0]}" -> ${word}: ${text.trim().slice(0, 80)}`);
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(source);
  return found;
}

describe("the glossary", () => {
  it("keeps engineering words and table names off business screens", () => {
    const files = ["components", "app"].flatMap((dir) => sourceFiles(join(SRC, dir)))
      .filter((file) => !TECHNICAL_FILES.has(relative(SRC, file)));
    expect(files.flatMap(violations)).toEqual([]);
  });

  it("calls the builder's nav item Build, so Explore means only the data set pages", () => {
    const shell = readFileSync(join(SRC, "components/AppShell.tsx"), "utf8");
    expect(shell).toMatch(/href: "\/build", label: "Build"/);
  });
});
