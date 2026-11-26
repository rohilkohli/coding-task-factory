// Finds functions and mutation sites in TypeScript sources using the
// TypeScript compiler API (exact positions; strings, comments, regex literals
// and template literals are never touched).
//
// Usage: node ts_scan.mjs <typescript-module-dir> <root> <file>...
// Prints JSON: [{file, name, start, bodyStart, bodyEnd, doc, sites: [...]}]
// Offsets are UTF-16 code-unit offsets into the file text (JS string indices).
import { createRequire } from "node:module";
import fs from "node:fs";
import path from "node:path";

const [tsDir, root, ...files] = process.argv.slice(2);
const ts = createRequire(import.meta.url)(tsDir);

const SITE_KINDS = new Map([
  [ts.SyntaxKind.EqualsEqualsEqualsToken, "==="],
  [ts.SyntaxKind.ExclamationEqualsEqualsToken, "!=="],
  [ts.SyntaxKind.EqualsEqualsToken, "=="],
  [ts.SyntaxKind.ExclamationEqualsToken, "!="],
  [ts.SyntaxKind.LessThanToken, "<"],
  [ts.SyntaxKind.LessThanEqualsToken, "<="],
  [ts.SyntaxKind.GreaterThanToken, ">"],
  [ts.SyntaxKind.GreaterThanEqualsToken, ">="],
  [ts.SyntaxKind.AmpersandAmpersandToken, "&&"],
  [ts.SyntaxKind.BarBarToken, "||"],
  [ts.SyntaxKind.PlusToken, "+"],
  [ts.SyntaxKind.MinusToken, "-"],
  [ts.SyntaxKind.QuestionQuestionToken, "??"],
]);

function functionName(node) {
  if (node.name && ts.isIdentifier(node.name)) return node.name.text;
  if (node.name && ts.isStringLiteral(node.name)) return node.name.text;
  // `export const X = (..) => {..}` / `X: function () {..}`
  const parent = node.parent;
  if (parent && (ts.isVariableDeclaration(parent) || ts.isPropertyAssignment(parent)) && ts.isIdentifier(parent.name)) {
    return parent.name.text;
  }
  // zod's `core.$constructor("$ZodX", (inst, def) => {..})`
  if (parent && ts.isCallExpression(parent) && parent.arguments.length >= 2 && ts.isStringLiteral(parent.arguments[0])) {
    return `${parent.arguments[0].text} (init)`;
  }
  return null;
}

function collectSites(body, sf) {
  const sites = [];
  const visit = (node) => {
    if (ts.isBinaryExpression(node) && SITE_KINDS.has(node.operatorToken.kind)) {
      // string concatenation is not an interesting arithmetic site
      const isConcat = node.operatorToken.kind === ts.SyntaxKind.PlusToken &&
        (ts.isStringLiteralLike(node.left) || ts.isStringLiteralLike(node.right) ||
         ts.isTemplateExpression(node.left) || ts.isTemplateExpression(node.right));
      if (!isConcat) {
        sites.push({ kind: "op", text: SITE_KINDS.get(node.operatorToken.kind),
                     start: node.operatorToken.getStart(sf), end: node.operatorToken.getEnd() });
      }
    } else if (ts.isPrefixUnaryExpression(node) && node.operator === ts.SyntaxKind.ExclamationToken) {
      sites.push({ kind: "not", text: "!", start: node.getStart(sf), end: node.getStart(sf) + 1 });
    } else if (node.kind === ts.SyntaxKind.TrueKeyword || node.kind === ts.SyntaxKind.FalseKeyword) {
      sites.push({ kind: "bool", text: node.getText(sf), start: node.getStart(sf), end: node.getEnd() });
    } else if (ts.isNumericLiteral(node) && /^\d+$/.test(node.text)) {
      sites.push({ kind: "int", text: node.getText(sf), start: node.getStart(sf), end: node.getEnd() });
    }
    // nested functions are reported as their own candidates
    if (node !== body && (ts.isFunctionLike(node) && node.body)) return;
    ts.forEachChild(node, visit);
  };
  visit(body);
  return sites;
}

// Statements whose deletion is a plausible wrong fix (declarations and returns
// are skipped: deleting them mostly yields type errors, a trivial "wrong fix").
function collectDeletions(body, sf) {
  const out = [];
  const visit = (node) => {
    if (node !== body && ts.isFunctionLike(node)) return;
    if (ts.isExpressionStatement(node) || ts.isIfStatement(node) || ts.isThrowStatement(node) ||
        ts.isForStatement(node) || ts.isForOfStatement(node) || ts.isForInStatement(node) ||
        ts.isWhileStatement(node)) {
      const start = node.getStart(sf);
      const lines = sf.getLineAndCharacterOfPosition(node.getEnd()).line -
        sf.getLineAndCharacterOfPosition(start).line;
      const parentIsElse = ts.isIfStatement(node.parent) && node.parent.elseStatement === node;
      const isAssertion = ts.isExpressionStatement(node) && /^(console\.)?assert\w*\(/.test(node.getText(sf));
      if (lines <= 8 && !parentIsElse && !isAssertion) {
        out.push({ kind: "stmt", text: node.getText(sf), start, end: node.getEnd() });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(body);
  return out;
}

const out = [];
for (const file of files) {
  const text = fs.readFileSync(file, "utf8");
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
  const visit = (node) => {
    if ((ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node) || ts.isArrowFunction(node) ||
         ts.isFunctionExpression(node) || ts.isGetAccessorDeclaration(node)) &&
        node.body && ts.isBlock(node.body)) {
      const name = functionName(node);
      if (name) {
        const docs = ts.getJSDocCommentsAndTags(node).map((d) => d.getText(sf));
        out.push({
          file: path.relative(root, file),
          name,
          start: node.getStart(sf),
          bodyStart: node.body.getStart(sf) + 1, // just after "{"
          bodyEnd: node.body.getEnd() - 1, // the closing "}"
          line: sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1,
          doc: docs.join("\n"),
          sites: collectSites(node.body, sf),
          deletions: collectDeletions(node.body, sf),
        });
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
}
process.stdout.write(JSON.stringify(out));
