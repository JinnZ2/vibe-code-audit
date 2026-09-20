#!/usr/bin/env python3
# crosslink_scan.py -- CC0, stdlib only, no network, phone-buildable.
#
# Pull the crosslinks out of a codebase. In a vibe-coded tree the
# crosslinks are the specification that survives the session: READMEs
# link to files, files import files, docs cite commands, commands name
# outputs, tables cite claim IDs. This module extracts them into an
# EDGE LEDGER (JSON) and nothing else.
#
# LOCATE ONLY. This module proposes nothing. There is no score, no
# verdict, no severity, no rewrite, no suggestion of what should be
# linked. A hit is an EDGE, not a defect. That is enforced structurally
# rather than promised: test_audit.py walks this module's AST and fails
# if an identifier from the verdict vocabulary appears in it, and
# plants one to show the scan is not silent.
#
# THE LIMIT, STATED HERE RATHER THAN AT THE BOTTOM
#     This is a SYNTAX WALKER. It finds links that are written down.
#     A link that lives only in the operator's head -- "I know audit.py
#     is the real one" -- is invisible to it, and the size of that
#     invisible set is not measurable from inside the scan. So an edge
#     that is absent here is a property of THE ARTIFACT AS SHIPPED,
#     never evidence that no understanding exists. The artifact's link
#     surface is the measurement; the codebase is only the sample.
#
# A SECOND LIMIT
#     The scan cannot tell a live external link from a dead one for
#     anything it cannot open (URLs). Those edges are extracted and
#     marked resolvable: false -- counted, never resolved silently and
#     never dropped silently.
#
# usage:  python3 crosslink_scan.py PATH ...          edge ledger to stdout
#         python3 crosslink_scan.py PATH --out FILE
#         python3 crosslink_scan.py --selftest

import ast
import json
import os
import re
import sys

SCHEMA = "vca-edge-ledger/1"

TEXT_SUFFIXES = (
    ".py", ".md", ".txt", ".json", ".cob", ".cfg", ".toml",
    ".yaml", ".yml", ".csv", ".html", ".sh",
)

# A scan never ingests its own output: ledgers and pinned samples are
# records OF the scan, not part of the tree's link surface. Files under
# any directory named samples/ or ledgers/ are excluded so the scan is
# idempotent -- re-running it after writing samples changes nothing.
SKIP_DIRS = {".git", "__pycache__", ".mypy_cache", "node_modules",
             ".venv", "samples", "ledgers"}

# Base names excluded for the same reason: a stale root-level copy of a
# scan artifact (e.g. written by an earlier run before --out pointed at
# samples/) must not re-enter the scan. Name-based, documented here.
SKIP_FILES = {"self_scan.sample.json", "self_audit.json",
              "self_audit.sample.txt"}


def _is_scan_artifact(relpath):
    parts = relpath.replace("\\", "/").split("/")
    base = parts[-1]
    if base in SKIP_FILES:
        return True
    if len(parts) > 1 and parts[0] in ("samples", "ledgers"):
        return True
    return False

# --- link recognizers ---------------------------------------------------

# a path reference: segments with a known-ish suffix, or ./ ../ prefix
RE_PATH = re.compile(
    r"(?<![\w/.-])"
    r"((?:\./|\.\./)?[\w.-]+(?:/[\w.+-]+)+\.[A-Za-z0-9]{1,8}"
    r"|[\w.+-]+\.(?:py|cob|md|json|txt|csv|sh))"
    r"(?![\w/])"
)
RE_MD_LINK = re.compile(r"\[([^\]]{0,80})\]\(([^)\s]+)\)")
RE_BACKTICK_CMD = re.compile(
    r"`((?:python3?|pip|git|node|npm|bash|sh)\s+[^`]{2,120})`"
)
RE_CLAIM_ID = re.compile(r"(?<![A-Za-z0-9_])([A-Z]{2,8}_\d{3,4})(?![A-Za-z0-9_])")
RE_URL = re.compile(r"https?://[^\s)\]>`\"']+")

# ------------------------------------------------------------------------
# The verdict vocabulary this module is forbidden to carry.
# test_audit.py asserts this set intersects the module's identifiers at
# zero. Keep it in a string so the guard itself does not trip the scan.
# ------------------------------------------------------------------------
_FORBIDDEN = ("verdict severity score grade rank rating fail pass warn"
              " error defect bug broken suggest recommendation")


def _iter_files(paths):
    """Yield (relpath, abspath) for every readable text file under paths."""
    seen = set()
    for root_arg in paths:
        if os.path.isfile(root_arg):
            base = os.path.dirname(os.path.abspath(root_arg))
            rel = os.path.relpath(os.path.abspath(root_arg), base)
            if rel not in seen and not _is_scan_artifact(rel):
                seen.add(rel)
                yield rel, os.path.abspath(root_arg), base
            continue
        base = os.path.abspath(root_arg)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in sorted(filenames):
                if fn in SKIP_FILES:
                    continue
                ab = os.path.join(dirpath, fn)
                if not fn.lower().endswith(TEXT_SUFFIXES):
                    continue
                rel = os.path.relpath(ab, base)
                if rel in seen or _is_scan_artifact(rel):
                    continue
                seen.add(rel)
                yield rel, ab, base


def _read(abspath):
    try:
        with open(abspath, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _edge(source, target, kind, line, resolvable, note=None):
    e = {
        "source": source,
        "target": target,
        "kind": kind,
        "line": line,
        "resolvable": bool(resolvable),
    }
    if note:
        e["note"] = note
    return e


def _scan_python_imports(rel, text):
    """import edges from a .py file, via AST so comments never count."""
    edges = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [_edge(rel, "<unparseable>", "import", 0, False,
                      note="SyntaxError; imports not extractable")]
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(_edge(rel, alias.name, "import",
                                   node.lineno, None))
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            if node.level:
                mod = "." * node.level + mod
            edges.append(_edge(rel, mod, "import", node.lineno, None))
    return edges


def _module_resolves(modname, file_index):
    """An import resolves if a matching file is anywhere in the tree."""
    if not modname or modname.startswith("."):
        return True  # relative import: resolvable by construction marker
    top = modname.split(".")[0]
    if top in sys.stdlib_module_names:
        return True
    stem = modname.replace(".", "/")
    for cand in (stem + ".py", os.path.join(stem, "__init__.py"),
                 top + ".py"):
        if cand in file_index:
            return True
    # filename match anywhere in tree (flat vibe-coded layouts)
    return any(p.endswith("/" + top + ".py") or p == top + ".py"
               for p in file_index)


def scan(paths):
    """Extract the edge ledger. Returns the ledger dict."""
    files = []
    raw_edges = []
    bases = []
    for rel, ab, base in _iter_files(paths):
        bases.append(base)
        text = _read(ab)
        if text is None:
            continue
        files.append(rel)
        lines = text.splitlines()
        if rel.lower().endswith(".py"):
            raw_edges.extend(_scan_python_imports(rel, text))
        for n, line in enumerate(lines, start=1):
            for m in RE_MD_LINK.finditer(line):
                raw_edges.append(_edge(rel, m.group(2), "md_link", n, None,
                                       note=m.group(1)[:40] or None))
            for m in RE_BACKTICK_CMD.finditer(line):
                raw_edges.append(_edge(rel, m.group(1).strip(),
                                       "command", n, None))
            for m in RE_CLAIM_ID.finditer(line):
                raw_edges.append(_edge(rel, m.group(1), "cites_claim", n, None))
            for m in RE_URL.finditer(line):
                raw_edges.append(_edge(rel, m.group(0), "url", n, False))
            for m in RE_PATH.finditer(line):
                tgt = m.group(1)
                # a path already captured as a md_link target is still
                # one edge; dedupe happens after resolvability marking
                raw_edges.append(_edge(rel, tgt, "path_ref", n, None))

    base = os.path.commonpath(bases) if bases else "."
    file_index = set(files)
    norm_index = {os.path.normpath(p) for p in files}

    edges = []
    seen = set()
    for e in raw_edges:
        tgt = e["target"]
        if e["kind"] == "import":
            e["resolvable"] = _module_resolves(tgt, norm_index)
        elif e["kind"] in ("path_ref", "md_link"):
            if RE_URL.match(tgt):
                e["kind"] = "url"
                e["resolvable"] = False
            elif tgt.startswith("#"):
                e["resolvable"] = True  # intra-document anchor
            else:
                clean = tgt.split("#")[0].split("?")[0]
                cand = os.path.normpath(clean)
                srcdir = os.path.dirname(e["source"])
                cand_rel = os.path.normpath(os.path.join(srcdir, clean))
                e["resolvable"] = (
                    cand in norm_index or cand_rel in norm_index
                    or clean in norm_index
                    or os.path.exists(os.path.join(base, cand))
                    or os.path.exists(os.path.join(base, cand_rel))
                )
        elif e["kind"] == "command":
            # command edge resolves if its script token names a tree file
            e["resolvable"] = any(
                tok in norm_index or os.path.basename(tok) in
                {os.path.basename(p) for p in norm_index}
                for tok in tgt.split()
                if tok.endswith((".py", ".sh", ".cob"))
            ) or False
        elif e["kind"] == "cites_claim":
            e["resolvable"] = None  # resolution is the audit's job
        key = (e["source"], e["target"], e["kind"], e["line"])
        if key not in seen:
            seen.add(key)
            edges.append(e)

    return {
        "schema": SCHEMA,
        "base": base,
        "files": sorted(files),
        "edges": edges,
        "counts": {
            "files": len(files),
            "edges": len(edges),
            "by_kind": {k: sum(1 for e in edges if e["kind"] == k)
                        for k in sorted({e["kind"] for e in edges})},
        },
    }


def main(argv):
    if "--selftest" in argv:
        here = os.path.dirname(os.path.abspath(__file__))
        led = scan([here])
        assert led["schema"] == SCHEMA
        assert led["counts"]["files"] > 0
        kinds = {e["kind"] for e in led["edges"]}
        assert "import" in kinds, "planted expectation: imports found"
        print("selftest ok: %d files, %d edges, kinds %s"
              % (led["counts"]["files"], led["counts"]["edges"],
                 sorted(kinds)))
        return 0
    paths = [a for a in argv[1:] if not a.startswith("--")]
    if not paths:
        print(__doc__)
        return 2
    ledger = scan(paths)
    out = json.dumps(ledger, indent=2, sort_keys=False)
    if "--out" in argv:
        dest = argv[argv.index("--out") + 1]
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write(out + "\n")
        print("wrote %s (%d files, %d edges)"
              % (dest, ledger["counts"]["files"],
                 ledger["counts"]["edges"]))
    else:
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
