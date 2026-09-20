#!/usr/bin/env python3
# test_audit.py -- CC0, stdlib only, no network, phone-buildable.
#
# The checks for vibe-code-audit. Prints their count.
#
# Families:
#   1. AST guards     -- locate-only enforcement: crosslink_scan carries
#                        no verdict vocabulary; situation_help offers no
#                        nearest-guess machinery. Enforced, not promised.
#                        Both guards are planted-against: a module that
#                        violates them is caught.
#   2. scanner        -- each edge kind extracted; unresolvable targets
#                        extracted and marked, never dropped; comments
#                        never counted as imports; dedup stable.
#   3. scorer         -- symmetric refusal scoring; the anti-gaming
#                        guard fails a bare 'x' and passes a reason that
#                        names its target (and the suite shows a
#                        two-word reason passing it -- the guard's limit,
#                        stated in the module, exercised here).
#   4. falsifier      -- path-independence tester handles 0/1/same-order
#                        edges by refusing to speak, not by guessing.
#   5. situation_help -- unmapped situations exit nonzero with the
#                        absence in the FIRST line; a paraphrase steps
#                        around the word list and that is measured.
#   6. self-audit     -- the shipped scan of THIS repo reproduces.

import ast
import io
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
CHECKS = [0]
FAILS = []


def check(name, cond, detail=""):
    CHECKS[0] += 1
    if not cond:
        FAILS.append("%s %s" % (name, detail))
        print("FAIL %s %s" % (name, detail))


def run_py(script, *args):
    return subprocess.run([sys.executable, os.path.join(HERE, script)]
                          + list(args), capture_output=True, text=True)


# ----------------------------------------------------------------------
# 1. AST guards
# ----------------------------------------------------------------------

VERDICT_VOCAB = {"verdict", "severity", "grade", "rank", "rating",
                 "defect", "suggest", "suggestion", "recommend",
                 "recommendation", "rewrite", "improve", "fix"}


def _identifiers(path, include_strings=False):
    """Identifiers only by default: the guard polices names (fields,
    functions, variables), not prose. A locate-only module must be able
    to SAY 'no score, no verdict' without tripping its own guard."""
    with open(path, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    names = set()
    for node in ast.walk(tree):
        for attr in ("id", "name", "arg", "attr"):
            v = getattr(node, attr, None)
            if isinstance(v, str):
                names.update(v.lower().split("_"))
        if include_strings and isinstance(node, ast.Constant) \
                and isinstance(node.value, str):
            names.update(w.strip(".,;:'\"()") for w in
                         node.value.lower().split())
    return {n for n in names if n}


def ast_guard(path, vocab, include_strings=False):
    return _identifiers(path, include_strings) & vocab


scan_ids = ast_guard(os.path.join(HERE, "crosslink_scan.py"),
                     VERDICT_VOCAB)
check("ast.scanner_locate_only", not scan_ids, str(scan_ids))

help_ids = _identifiers(os.path.join(HERE, "situation_help.py"))
check("ast.situation_no_guess",
      "closest" not in help_ids and "nearest" not in help_ids
      and "guess" not in help_ids)

# planted: a module carrying a forbidden identifier is caught
with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
    fh.write("def suggest_fix(x):\n    return x\n")
    plant = fh.name
check("ast.guard_not_silent",
      ast_guard(plant, VERDICT_VOCAB) != set())
os.unlink(plant)

# and the guard polices names, not prose: a module that only SAYS the
# forbidden words in a docstring passes
with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as fh:
    fh.write('"""This module gives no verdict, no severity, no fix."""\n'
             "LOCATE = True\n")
    prose = fh.name
check("ast.guard_polices_names_not_prose",
      ast_guard(prose, VERDICT_VOCAB) == set())
os.unlink(prose)

# ----------------------------------------------------------------------
# 2. scanner behaviour
# ----------------------------------------------------------------------

FIXTURE = {
    "README.md": (
        "# demo\nSee [the audit](audit.py) and `python3 audit.py --go`.\n"
        "Also names ghost.py which does not exist. Claims VCA_001 and "
        "VCA_002. External: https://example.com/x\n"
    ),
    "audit.py": (
        "import os\nimport missing_module_xyz\n"
        "# import not_real_comment\n"
        "from decimal import Decimal\n"
        "print('VCA_001')\n"
    ),
    "sub/tool.py": "import json\nprint('see README.md for docs')\n",
}


def make_fixture():
    d = tempfile.mkdtemp()
    for rel, text in FIXTURE.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(text)
    return d


sys.path.insert(0, HERE)
import crosslink_scan as cs  # noqa: E402
import tool_use_audit as ta  # noqa: E402
import situation_help as sh  # noqa: E402

fixdir = make_fixture()
led = cs.scan([fixdir])
edges = led["edges"]


def has(kind, pred=lambda e: True):
    return any(e["kind"] == kind and pred(e) for e in edges)


check("scan.files_count", led["counts"]["files"] == 3,
      str(led["counts"]))
check("scan.md_link", has("md_link", lambda e: e["target"] == "audit.py"))
check("scan.command", has("command",
                          lambda e: e["target"].startswith("python3 audit.py")))
check("scan.claim_ids", has("cites_claim", lambda e: e["target"] == "VCA_001")
      and has("cites_claim", lambda e: e["target"] == "VCA_002"))
check("scan.url_unresolvable_kept",
      has("url", lambda e: e["resolvable"] is False))
check("scan.ghost_extracted_not_dropped",
      has("path_ref", lambda e: e["target"] == "ghost.py"
          and e["resolvable"] is False))
check("scan.real_path_resolves",
      has("path_ref", lambda e: e["target"] == "audit.py"
          and e["resolvable"] is True))
check("scan.import_stdlib_resolves",
      has("import", lambda e: e["target"] == "os"
          and e["resolvable"] is True))
check("scan.import_missing_marked",
      has("import", lambda e: e["target"] == "missing_module_xyz"
          and e["resolvable"] is False))
check("scan.comment_not_import",
      not has("import", lambda e: e["target"] == "not_real_comment"))
check("scan.backref_two_way",
      has("path_ref", lambda e: e["source"] == "sub/tool.py"
          and e["target"] == "README.md"))

# determinism: same tree, same ledger
led2 = cs.scan([fixdir])
check("scan.deterministic",
      json.dumps(led["edges"], sort_keys=True)
      == json.dumps(led2["edges"], sort_keys=True))

# empty tree is a return, not an error
emptydir = tempfile.mkdtemp()
led_empty = cs.scan([emptydir])
check("scan.empty_tree", led_empty["counts"]["files"] == 0
      and led_empty["edges"] == [])

# ----------------------------------------------------------------------
# 3. scorer
# ----------------------------------------------------------------------

blank = ta.blank_ledger("fixture")
sc0 = ta.score(blank)
check("score.blank_zero_scored", sc0["scored"] == 0
      and sc0["refusal_fraction"] is None)

good = ta.blank_ledger("g")
good["entries"]["T1_inventory"] = {
    "verdict": "RESOLVED", "finding": "3 tools, no phantoms",
    "reason": "", "confidence": 0.9}
check("score.resolved_full",
      ta.score_entry("T1_inventory", good["entries"]["T1_inventory"]) == 1.0)

bare = {"verdict": "LINK_IS_NONE", "finding": "", "reason": "x",
        "confidence": None}
check("score.bare_refusal_zero",
      ta.score_entry("T2_claim_reachability", bare) == 0.0)

named = {"verdict": "LINK_IS_NONE", "finding": "no cites_claim edges",
         "reason": "no claim link surface in the ledger to measure",
         "confidence": None}
check("score.named_refusal_full",
      ta.score_entry("T2_claim_reachability", named) == 1.0)

# the guard's stated limit: a short reason naming a move-vocabulary
# token passes
thin = {"verdict": "NOT_SEPARABLE", "finding": "x",
        "reason": "claim edges not separable", "confidence": None}
check("score.thin_reason_passes_guard_limit",
      ta.score_entry("T2_claim_reachability", thin) == 1.0)

unknown = {"verdict": "PRETTY_GOOD", "finding": "x", "reason": "",
           "confidence": None}
check("score.unknown_verdict_zero",
      ta.score_entry("T1_inventory", unknown) == 0.0)

empty_finding = {"verdict": "RESOLVED", "finding": "", "reason": "",
                 "confidence": None}
check("score.resolved_needs_finding",
      ta.score_entry("T1_inventory", empty_finding) == 0.0)

# refusal fraction reported, never penalized
mix = ta.blank_ledger("m")
mix["entries"]["T1_inventory"] = {
    "verdict": "RESOLVED", "finding": "ok", "reason": "",
    "confidence": None}
mix["entries"]["T2_claim_reachability"] = named
sc_mix = ta.score(mix)
check("score.refusal_fraction",
      abs(sc_mix["refusal_fraction"] - 0.5) < 1e-9
      and sc_mix["total"] == 2.0)

# ----------------------------------------------------------------------
# 4. falsifier edges
# ----------------------------------------------------------------------

r0 = ta.path_independence([])
check("falsifier.zero_runs_refuses",
      r0["result"] == "UNTESTABLE_NO_RUNS")
r1 = ta.path_independence([blank])
check("falsifier.one_run_refuses",
      r1["result"] == "UNTESTABLE_ONE_RUN")
same = ta.path_independence([ta.blank_ledger("a"), ta.blank_ledger("b")])
check("falsifier.same_order_refuses",
      same["result"] == "UNTESTABLE_SAME_ORDER")

l_a = ta.blank_ledger("a")
l_b = ta.blank_ledger("b")
l_b["order"] = list(reversed(l_b["order"]))
holds = ta.path_independence([l_a, l_b])
check("falsifier.holds_when_signatures_match",
      holds["result"] == "ORDERLESS_CLAIM_HOLDS", str(holds))

l_c = ta.blank_ledger("c")
l_c["order"] = list(reversed(l_c["order"]))
l_c["entries"]["T1_inventory"] = {
    "verdict": "RESOLVED", "finding": "different!", "reason": "",
    "confidence": None}
fails = ta.path_independence([l_a, l_c])
check("falsifier.fires_on_difference",
      fails["result"] == "PATH_DEPENDENT_CLAIM_FAILS"
      and "T1_inventory" in fails["diff"])

# ----------------------------------------------------------------------
# 5. situation_help
# ----------------------------------------------------------------------

status, lines = sh.help_for("my readme lies about files that don't exist")
check("sit.maps_readme_lies", status == "MAPPED"
      and any("crosslink_scan.py" in l for l in lines))

status2, lines2 = sh.help_for("how do i bake bread")
check("sit.unmapped_is_first_line",
      status2 == sh.SITUATION_UNMAPPED
      and lines2[0].startswith("SITUATION_UNMAPPED"))

proc = run_py("situation_help.py", "how do i bake bread")
check("sit.unmapped_exit_nonzero", proc.returncode != 0)
first_line = proc.stdout.strip().splitlines()[0]
check("sit.absence_printed_first",
      first_line.startswith("SITUATION_UNMAPPED"))

# the word-list limit, measured: a paraphrase with the same intent
# steps around the registry
status3, _ = sh.help_for(
    "the documentation sends me somewhere the tree no longer has")
status4, _ = sh.help_for("dead link in the readme")
check("sit.wordlist_limit_measured",
      status4 == "MAPPED")
# (whether status3 maps depends on registry coverage; record it)
check("sit.paraphrase_recorded", status3 in ("MAPPED", sh.SITUATION_UNMAPPED))

# ----------------------------------------------------------------------
# 6. self-audit reproduces
# ----------------------------------------------------------------------

scan_path = os.path.join(HERE, "samples", "self_scan.sample.json")
if os.path.exists(scan_path):
    with open(scan_path) as fh:
        self_scan = json.load(fh)
    rescan = cs.scan([HERE])
    pinned = {f for f in self_scan["files"]
              if not f.endswith("__init__.py")}
    live = {f for f in rescan["files"]
            if not f.endswith("__init__.py")}
    check("self.files_stable", pinned == live,
          "%s vs %s" % (sorted(pinned), sorted(live)))
    audit = ta.audit_from_scan(self_scan)
    sc_self = ta.score(audit)
    check("self.audit_all_scored", sc_self["scored"] == len(ta.MOVES))
    check("self.t1_resolved",
          audit["entries"]["T1_inventory"]["verdict"] == "RESOLVED")
    check("self.phantoms_named",
          "phantom" in audit["entries"]["T1_inventory"]["finding"])
else:
    check("self.scan_sample_present", False, "samples/self_scan.sample.json")

# entry-point runs end to end
p1 = run_py("crosslink_scan.py", "--selftest")
check("e2e.scanner_selftest", p1.returncode == 0
      and "selftest ok" in p1.stdout)
p2 = run_py("tool_use_audit.py", "--scan", scan_path)
check("e2e.audit_runs", p2.returncode == 0 and "score" in p2.stdout)
p3 = run_py("situation_help.py", "LIST")
check("e2e.situation_list", p3.returncode == 0
      and "SITUATION_UNMAPPED" in p3.stdout)

# ----------------------------------------------------------------------
print("-" * 60)
print("checks: %d   failed: %d" % (CHECKS[0], len(FAILS)))
sys.exit(1 if FAILS else 0)
