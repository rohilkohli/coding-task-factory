"""Language-aware code operations for the task generator.

* find_functions(lang, root, files) -> list[Function]
    Python: `ast` + `tokenize` (exact).  TypeScript: the TypeScript compiler API
    via ts_scan.mjs (exact).  C++: a small lexer that skips comments, string,
    char and raw-string literals and preprocessor lines, plus brace matching.
* Mutation sites inside each function body (operators, negations, boolean and
  integer literals) are reported with exact offsets, so a mutation never
  touches strings or comments.
* mutations_for(site) lists the replacement texts for a site.
* removal_stub(lang, fn, text) returns the file text with the function body
  replaced by a "not implemented" stub (signature and docs kept).
"""

from __future__ import annotations

import ast
import io
import json
import re
import subprocess
import tokenize
from dataclasses import dataclass, field
from pathlib import Path

FACTORY = Path(__file__).resolve().parent


@dataclass
class Site:
    kind: str  # op | not | bool | int
    text: str
    start: int  # char offset in file text
    end: int


@dataclass
class Function:
    file: str  # relative to the repo root
    name: str
    line: int
    start: int  # offset of the definition
    body_start: int  # offset where the replaceable body begins
    body_end: int  # offset where it ends (exclusive)
    doc: str = ""
    sites: list[Site] = field(default_factory=list)

    @property
    def body_lines(self) -> int:
        return 0  # filled by caller with the text if needed


# --------------------------------------------------------------------------
# Mutation operators (shared by all languages; applicability is per site)

OP_SWAPS = {
    "==": ["!="], "!=": ["=="], "===": ["!=="], "!==": ["==="],
    "<": ["<=", ">"], "<=": ["<", ">="], ">": [">=", "<"], ">=": [">", "<="],
    "&&": ["||"], "||": ["&&"], "and": ["or"], "or": ["and"],
    "+": ["-"], "-": ["+"], "??": ["||"],
    "is": ["is not"], "is not": ["is"], "in": ["not in"], "not in": ["in"],
}
BOOL_SWAPS = {"True": "False", "False": "True", "true": "false", "false": "true"}


def mutations_for(site: Site) -> list[str]:
    if site.kind == "op":
        return OP_SWAPS.get(site.text, [])
    if site.kind == "not":
        return [""]  # drop the negation
    if site.kind == "bool":
        return [BOOL_SWAPS[site.text]]
    if site.kind == "int":
        n = int(site.text)
        return [str(n + 1)] + ([str(n - 1)] if n > 0 else [])
    return []


# --------------------------------------------------------------------------
# Python

def _line_offsets(text: str) -> list[int]:
    offsets, pos = [0], 0
    for line in text.splitlines(keepends=True):
        pos += len(line)
        offsets.append(pos)
    return offsets


def _python_functions(root: Path, rel: str) -> list[Function]:
    text = (root / rel).read_text()
    tree = ast.parse(text)
    lines = _line_offsets(text)
    to_off = lambda ln, col: lines[ln - 1] + col  # noqa: E731

    # token sites for the whole file, filtered per function below
    tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    sites: list[Site] = []
    for i, tok in enumerate(tokens):
        s, e = to_off(*tok.start), to_off(*tok.end)
        if tok.type == tokenize.OP and tok.string in ("==", "!=", "<", "<=", ">", ">=", "+", "-"):
            prev = tokens[i - 1] if i else None
            # only binary +/-: previous token must end an operand
            if tok.string in "+-" and not (prev and (prev.type in (tokenize.NAME, tokenize.NUMBER, tokenize.STRING)
                                                     or prev.string in (")", "]", "}"))):
                continue
            sites.append(Site("op", tok.string, s, e))
        elif tok.type == tokenize.NAME:
            nxt = tokens[i + 1] if i + 1 < len(tokens) else None
            prev = tokens[i - 1] if i else None
            if tok.string in ("and", "or"):
                sites.append(Site("op", tok.string, s, e))
            elif tok.string == "is":
                if nxt and nxt.string == "not":
                    sites.append(Site("op", "is not", s, to_off(*nxt.end)))
                else:
                    sites.append(Site("op", "is", s, e))
            elif tok.string == "not":
                if prev and prev.string == "is":
                    continue
                if nxt and nxt.string == "in":
                    sites.append(Site("op", "not in", s, to_off(*nxt.end)))
                else:
                    # drop "not " (including the following space)
                    sites.append(Site("not", text[s:to_off(*nxt.start)] if nxt else "not", s,
                                      to_off(*nxt.start) if nxt else e))
            elif tok.string == "in" and not (prev and prev.string == "not"):
                # `for x in y` is syntax, not a membership test
                line_text = tok.line.lstrip()
                if not line_text.startswith("for ") and " for " not in line_text:
                    sites.append(Site("op", "in", s, e))
            elif tok.string in ("True", "False"):
                sites.append(Site("bool", tok.string, s, e))
        elif tok.type == tokenize.NUMBER and tok.string.isdigit():
            sites.append(Site("int", tok.string, s, e))

    out: list[Function] = []
    class_stack: list[str] = []

    def visit(node, prefix=""):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                visit(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = child.body
                doc = ast.get_docstring(child) or ""
                stmts = body[1:] if doc and isinstance(body[0], ast.Expr) else body
                if not stmts:
                    continue
                b_start = to_off(stmts[0].lineno, 0)
                b_end = to_off(stmts[-1].end_lineno, stmts[-1].end_col_offset)
                fn = Function(rel, prefix + child.name, child.lineno, to_off(child.lineno, child.col_offset),
                              b_start, b_end, doc)
                fn.sites = [st for st in sites if b_start <= st.start and st.end <= b_end]
                out.append(fn)
                visit(child, f"{prefix}{child.name}.<locals>.")
    visit(tree)
    # nested functions: keep sites only in the innermost function
    return out


# --------------------------------------------------------------------------
# C++

_CPP_OPS = ["==", "!=", "<=", ">=", "&&", "||", "<", ">", "+", "-"]


def _cpp_code_mask(text: str) -> list[bool]:
    """True for characters that are code (not comment/string/char/preprocessor)."""
    mask = [True] * len(text)
    i, n = 0, len(text)
    at_line_start = True
    while i < n:
        c = text[i]
        if at_line_start and c == "#":
            j = i
            while j < n and not (text[j] == "\n" and text[j - 1] != "\\"):
                j += 1
            for k in range(i, j):
                mask[k] = False
            i = j
            continue
        if c == "\n":
            at_line_start = True
            i += 1
            continue
        if not c.isspace():
            at_line_start = False
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
        elif c == "R" and i + 1 < n and text[i + 1] == '"':
            m = re.match(r'R"([^(\s]*)\(', text[i:])
            if not m:
                i += 1
                continue
            close = ")" + m.group(1) + '"'
            j = text.find(close, i + m.end())
            j = n if j < 0 else j + len(close)
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            j += 1
        else:
            i += 1
            continue
        for k in range(i, min(j, n)):
            mask[k] = False
        i = j
    return mask


def _cpp_doc(text: str, def_start: int) -> str:
    """The comment block directly above a definition, if any."""
    lines = text[:def_start].rstrip("\n").split("\n")
    doc: list[str] = []
    while lines and lines[-1].strip().startswith(("//", "*", "/*")):
        doc.insert(0, lines.pop().strip())
        if doc[0].startswith("/*"):
            break
    return "\n".join(doc)


def _cpp_functions(root: Path, rel: str) -> list[Function]:
    text = (root / rel).read_text()
    mask = _cpp_code_mask(text)
    code = "".join(ch if m else (" " if ch != "\n" else "\n") for ch, m in zip(text, mask))

    out: list[Function] = []
    stack: list[dict] = []  # open braces: {"kind", "at", "name", "header_at"}
    seg_start = 0  # start of the current declaration
    for i, ch in enumerate(code):
        if ch == ";":
            seg_start = i + 1
        elif ch == "{":
            header = code[seg_start:i].strip()
            if any(b["kind"] == "function" for b in stack):
                kind = "block"
            elif re.match(r"^(namespace\b|extern\s)", header) or (header == "" and not stack):
                kind = "namespace"
            elif re.search(r"\b(class|struct|union|enum)\b[^()]*$", header):
                kind = "class"
            elif re.search(r"\)\s*(const\s*)?(noexcept\s*)?(override\s*)?(final\s*)?$", header) or \
                    re.search(r"\)\s*:\s*[\w:]+\s*[({]", header):
                kind = "function"
            else:
                kind = "block"
            entry = {"kind": kind, "at": i}
            if kind == "function":
                head = header.split("(")[0].split()
                entry["name"] = head[-1] if head else "?"
                entry["header_at"] = seg_start + (len(code[seg_start:i]) - len(code[seg_start:i].lstrip()))
            stack.append(entry)
            seg_start = i + 1
        elif ch == "}":
            if stack:
                b = stack.pop()
                if b["kind"] == "function":
                    def_start = b["header_at"]
                    fn = Function(rel, b["name"], text.count("\n", 0, def_start) + 1, def_start, b["at"] + 1, i,
                                  _cpp_doc(text, def_start))
                    fn.sites = _cpp_sites(text, code, b["at"] + 1, i)
                    out.append(fn)
            seg_start = i + 1
    return out


def _cpp_sites(text: str, code: str, start: int, end: int) -> list[Site]:
    sites = []
    i = start
    while i < end:
        if code[i].isspace():
            i += 1
            continue
        matched = False
        for op in _CPP_OPS:
            if code.startswith(op, i):
                # binary operators are space-separated in this (clang-formatted) code;
                # that excludes templates, ->, ++, --, <<, >> and unary minus.
                if code[i - 1] == " " and code[i + len(op): i + len(op) + 1] == " " \
                        and code[i - 2] not in "=<>!&|+-" and code[i + len(op) + 1] not in "=<>&|":
                    sites.append(Site("op", op, i, i + len(op)))
                i += len(op)
                matched = True
                break
        if matched:
            continue
        if code[i] == "!" and code[i + 1] != "=":
            sites.append(Site("not", "!", i, i + 1))
            i += 1
            continue
        m = re.match(r"[A-Za-z_]\w*|\d+[\w.]*", code[i:end])
        if m:
            tok = m.group(0)
            if tok in ("true", "false"):
                sites.append(Site("bool", tok, i, i + len(tok)))
            elif tok.isdigit():
                sites.append(Site("int", tok, i, i + len(tok)))
            i += len(tok)
            continue
        i += 1
    return sites


# --------------------------------------------------------------------------
# TypeScript

def _ts_functions(root: Path, rels: list[str], ts_module: Path) -> list[Function]:
    proc = subprocess.run(["node", str(FACTORY / "ts_scan.mjs"), str(ts_module), str(root),
                           *[str(root / r) for r in rels]],
                          check=True, capture_output=True, text=True)
    out = []
    texts = {r: (root / r).read_text() for r in rels}
    for item in json.loads(proc.stdout):
        text = texts[item["file"]]
        fn = Function(item["file"], item["name"], item["line"], item["start"], item["bodyStart"],
                      item["bodyEnd"], item["doc"])
        # JS offsets are UTF-16 units; keep only sites whose text matches here
        fn.sites = [Site(s["kind"], s["text"], s["start"], s["end"]) for s in item["sites"]
                    if text[s["start"]:s["end"]] == s["text"]]
        if text[fn.body_start - 1:fn.body_start] == "{" and text[fn.body_end:fn.body_end + 1] == "}":
            out.append(fn)
    return out


# --------------------------------------------------------------------------

def find_functions(lang: str, root: Path, rels: list[str], ts_module: Path | None = None) -> list[Function]:
    if lang == "python":
        return [f for rel in rels for f in _python_functions(root, rel)]
    if lang == "cpp":
        return [f for rel in rels for f in _cpp_functions(root, rel)]
    if lang == "typescript":
        assert ts_module is not None
        return _ts_functions(root, rels, ts_module)
    raise ValueError(lang)


def removal_stub(lang: str, fn: Function, text: str) -> str:
    """File text with fn's body replaced by a not-implemented stub."""
    if lang == "python":
        line_start = text.rfind("\n", 0, fn.body_start) + 1
        indent = re.match(r"[ \t]*", text[line_start:]).group(0) or "    "
        stub = f'{indent}raise NotImplementedError("{fn.name.rsplit(".", 1)[-1]} is not implemented")'
        return text[:line_start] + stub + text[fn.body_end:]
    if lang == "typescript":
        line_start = text.rfind("\n", 0, fn.start) + 1
        indent = re.match(r"[ \t]*", text[line_start:]).group(0)
        stub = f'\n{indent}  throw new Error("not implemented");\n{indent}'
        return text[:fn.body_start] + stub + text[fn.body_end:]
    if lang == "cpp":
        stub = '\n  throw std::logic_error("not implemented");\n'
        new = text[:fn.body_start] + stub + text[fn.body_end:]
        if "#include <stdexcept>" not in new:
            first_include = new.find("#include")
            new = new[:first_include] + "#include <stdexcept>\n" + new[first_include:]
        return new
    raise ValueError(lang)


def cpp_header_doc(root: Path, fn: Function, header_globs: tuple[str, ...] = ("include/**/*.h",)) -> str:
    """Documentation comment above a method's declaration in the public headers."""
    method = fn.name.split("::")[-1]
    if not re.match(r"^~?\w+$", method):
        return ""
    for pattern in header_globs:
        for header in sorted(root.glob(pattern)):
            lines = header.read_text().split("\n")
            for i, line in enumerate(lines):
                if re.search(rf"(^|[\s*&~]){re.escape(method)}\s*\(", line) and not line.strip().startswith(("//", "*")):
                    doc = []
                    j = i - 1
                    while j >= 0 and lines[j].strip().startswith(("//", "*", "/*")):
                        doc.insert(0, lines[j].strip())
                        if lines[j].strip().startswith("/*"):
                            break
                        j -= 1
                    if doc:
                        return f"// from {header.relative_to(root)}\n" + "\n".join(doc) + "\n" + line.strip()
    return ""
