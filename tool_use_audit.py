#!/usr/bin/env python3
# tool_use_audit.py -- CC0, stdlib only, no network, phone-buildable.
#
# The audit. Reads an edge ledger produced by crosslink_scan.py and
# measures four things about a vibe-coded codebase, all from the
# crosslinks, none from the prose's self-description:
#
#   TOOL        what instruments exist -- declared, runnable, phantom
#   TOOL_USE    are tools connected to the claims they produce
#   SITUATION   does the artifact name the situation it is for
#   HELP_FULL   is help FULL -- reachable, current, claim-connected,
#               and two-way
#
# SCORING RULE THIS MODULE EXISTS FOR
#     A correctly-refused verdict scores as high as a correct one.
#     REFUSALS = {NOT_DERIVABLE, NOT_SEPARABLE, NOT_ADDRESSABLE,
#     LINK_IS_NONE, INSTRUMENT_BLIND} each score 1.0 exactly as
#     RESOLVED does, and refusal_fraction is reported, never penalized.
#     A vibe-coded artifact with no crosslinks is not a zero; it is a
#     ledger full of LINK_IS_NONE, which is a finding about the
#     artifact, not a failure of the audit.
#
# THE ANTI-GAMING GUARD, AND ITS LIMIT, STATED HERE
#     A bare "x" is not a refusal and scores zero. Every refused cell
#     must carry a reason string that names WHAT cannot be seen --
#     enforced: reason must contain at least one token from the cell's
#     own target or measurand vocabulary. This is a guard against the
#     empty refusal, not against a determined one; a two-word reason
#     that names the target passes it, and the suite shows that. The
#     repair would be human review, which is out of scope and is not
#     claimed.
#
# usage:  python3 tool_use_audit.py --scan FILE     audit from edge ledger
#         python3 tool_use_audit.py --ledger FILE   score a filled ledger
#         python3 tool_use_audit.py --emit "name"   move set + blank ledger
#         python3 tool_use_audit.py --paths L1 L2   falsifier: same moves,
#                                                   different orders

import json
import os
import re
import sys

SCHEMA = "vca-audit-ledger/1"

REFUSALS = frozenset([
    "NOT_DERIVABLE", "NOT_SEPARABLE", "NOT_ADDRESSABLE",
    "LINK_IS_NONE", "INSTRUMENT_BLIND",
])
RESOLVED = "RESOLVED"

# ---------------------------------------------------------------------
# MOVES -- trigger is a property of the edge ledger, not of the last
# answer. That is what makes them orderless; the falsifier below tests
# it rather than assuming it.
# ---------------------------------------------------------------------

MOVES = {
    "T1_inventory": {
        "measurand": "TOOL",
        "trigger": "ledger has files",
        "ask": "Which files are instruments? For each: declared by a doc "
               "edge, runnable (import-resolvable), or phantom (named, "
               "absent from the tree)?",
        "admits": [RESOLVED, "NOT_DERIVABLE", "LINK_IS_NONE"],
    },
    "T2_claim_reachability": {
        "measurand": "TOOL_USE",
        "trigger": "ledger has cites_claim edges",
        "ask": "Is every cited claim ID reachable from an entry point "
               "through edges that could recompute it, or is it "
               "CLAIM_UNREACHABLE -- cited by prose, produced by nothing "
               "the tree connects?",
        "admits": [RESOLVED, "NOT_SEPARABLE", "LINK_IS_NONE"],
    },
    "T3_doc_currency": {
        "measurand": "HELP_FULL",
        "trigger": "ledger has doc->file edges",
        "ask": "Does every file a doc names exist and resolve? An "
               "unresolvable doc edge is stale help: it sends the reader "
               "somewhere the tree no longer has.",
        "admits": [RESOLVED, "NOT_ADDRESSABLE", "LINK_IS_NONE"],
    },
    "T4_two_way": {
        "measurand": "HELP_FULL",
        "trigger": "ledger has path_ref edges in both directions",
        "ask": "Does the link run both ways -- doc names file AND file "
               "names doc? One-way help is half-full by construction.",
        "admits": [RESOLVED, "NOT_SEPARABLE", "LINK_IS_NONE"],
    },
    "T5_situation_declared": {
        "measurand": "SITUATION",
        "trigger": "ledger has any md/README surface",
        "ask": "Does the artifact state which situation it is for, in a "
               "place the scan can see? A situation carried only in the "
               "operator's session is invisible to the ledger and scores "
               "INSTRUMENT_BLIND, not zero.",
        "admits": [RESOLVED, "INSTRUMENT_BLIND", "LINK_IS_NONE"],
    },
    "T6_absence_named": {
        "measurand": "TOOL_USE",
        "trigger": "any measurand returned a refusal",
        "ask": "Is the absence named as a value -- UNMET-style -- or "
               "smoothed into an empty section? The absence must be "
               "selectable as a first-class cell.",
        "admits": [RESOLVED, "NOT_ADDRESSABLE", "LINK_IS_NONE"],
    },
}

ENTRY_POINT_RE = re.compile(
    r"(?:^|/)(?:entry|main|run|demo|cli|audit|scan|sim)[\w.-]*\.py$")


# ---------------------------------------------------------------------
# ledger schema helpers
# ---------------------------------------------------------------------

def blank_ledger(artifact):
    return {
        "schema": SCHEMA,
        "artifact": artifact,
        "order": list(MOVES),
        "entries": {mv: {"verdict": None, "finding": "", "reason": "",
                         "confidence": None} for mv in MOVES},
    }


def _reason_names_target(entry, move_id):
    """The anti-gaming guard: a refusal's reason must contain at least
    one token (>=4 chars) from the move's measurand or trigger text, or
    from the entry's own finding. A bare 'x' cannot pass."""
    reason = (entry.get("reason") or "").lower()
    if len(reason) < 8:
        return False
    vocab = set()
    mv = MOVES[move_id]
    for text in (mv["measurand"], mv["trigger"], mv["ask"],
                 entry.get("finding") or ""):
        vocab.update(t for t in re.findall(r"[a-z_]{4,}", text.lower()))
    return any(t in reason for t in vocab)


def score_entry(move_id, entry):
    v = entry.get("verdict")
    if v is None:
        return None
    if v == RESOLVED:
        return 1.0 if (entry.get("finding") or "").strip() else 0.0
    if v in REFUSALS:
        return 1.0 if _reason_names_target(entry, move_id) else 0.0
    return 0.0


def score(ledger):
    entries = ledger.get("entries", {})
    per_move, total, n = {}, 0.0, 0
    refusals = 0
    for mv in MOVES:
        s = score_entry(mv, entries.get(mv, {}))
        per_move[mv] = s
        if s is not None:
            total += s
            n += 1
            if entries[mv].get("verdict") in REFUSALS:
                refusals += 1
    return {
        "per_move": per_move,
        "total": total,
        "possible": len(MOVES),
        "scored": n,
        "refusal_fraction": (refusals / n) if n else None,
        "moves_not_run": [mv for mv in MOVES if per_move[mv] is None],
    }


def path_independence(ledgers):
    """Falsifier for 'the moves are orderless'.

    Preconditions enforced, not assumed: at least two ledgers, and at
    least two distinct orderings among them -- otherwise the claim is
    UNTESTABLE, reported as such. At zero ledgers the claim cannot
    speak; at one it cannot compare; both edges named, neither
    smoothed."""
    if len(ledgers) == 0:
        return {"result": "UNTESTABLE_NO_RUNS",
                "detail": "zero ledgers; the claim cannot speak"}
    if len(ledgers) == 1:
        return {"result": "UNTESTABLE_ONE_RUN",
                "detail": "one ledger; nothing to compare across orders"}
    orders = [tuple(l.get("order", [])) for l in ledgers]
    if len(set(orders)) < 2:
        return {"result": "UNTESTABLE_SAME_ORDER",
                "detail": "all ledgers used the same order; "
                          "path-independence was not exercised"}
    def signature(l):
        return {mv: (e.get("verdict"), (e.get("finding") or "").strip())
                for mv, e in l.get("entries", {}).items()}
    sigs = [signature(l) for l in ledgers]
    if all(s == sigs[0] for s in sigs):
        return {"result": "ORDERLESS_CLAIM_HOLDS",
                "detail": "%d runs, %d distinct orders, identical "
                          "(move, verdict, finding) sets"
                          % (len(ledgers), len(set(orders)))}
    diff = [mv for mv in MOVES
            if len({s.get(mv) for s in sigs}) > 1]
    return {"result": "PATH_DEPENDENT_CLAIM_FAILS",
            "detail": "moves differing across orders: %s" % diff,
            "diff": diff}


# ---------------------------------------------------------------------
# auto-audit from a scan: fills the ledger where the graph answers,
# refuses where it cannot
# ---------------------------------------------------------------------

def audit_from_scan(scan):
    led = blank_ledger(scan.get("base", "<unnamed>"))
    led["schema"] = SCHEMA
    files = set(scan.get("files", []))
    edges = scan.get("edges", [])
    by_kind = {}
    for e in edges:
        by_kind.setdefault(e["kind"], []).append(e)

    doc_files = {f for f in files if f.lower().endswith((".md", ".txt"))}
    py_files = {f for f in files if f.lower().endswith(".py")}
    entry_points = {f for f in py_files if ENTRY_POINT_RE.search(f)}

    # --- T1 inventory -------------------------------------------------
    doc_named = {e["target"].split("#")[0] for e in
                 by_kind.get("path_ref", []) + by_kind.get("md_link", [])
                 if e["source"] in doc_files and e["target"].endswith(".py")}
    doc_named_basenames = {os.path.basename(t) for t in doc_named}
    phantom = sorted(t for t in doc_named
                     if t not in files
                     and os.path.basename(t) not in
                     {os.path.basename(f) for f in files})
    runnable = sorted(f for f in py_files
                      if f in entry_points
                      or os.path.basename(f) in doc_named_basenames)
    if not py_files:
        led["entries"]["T1_inventory"].update(
            verdict="LINK_IS_NONE",
            reason="ledger carries no python files; the instrument "
                   "inventory measurand has no file surface to read",
            finding="no .py files in scan")
    else:
        led["entries"]["T1_inventory"].update(
            verdict=RESOLVED,
            finding=("files=%d, entry_points=%d, doc-named=%d, "
                     "phantom(doc-named but absent)=%s"
                     % (len(py_files), len(entry_points),
                        len(doc_named), phantom or "none")))

    # --- T2 claim reachability ---------------------------------------
    cited = sorted({e["target"] for e in by_kind.get("cites_claim", [])})
    if not cited:
        led["entries"]["T2_claim_reachability"].update(
            verdict="LINK_IS_NONE",
            reason="no cites_claim edges in the ledger; claim "
                   "reachability has no link surface to measure",
            finding="no claim IDs cited anywhere")
    else:
        producers = set()
        for e in by_kind.get("cites_claim", []):
            if e["source"] in py_files:
                producers.add(e["target"])
        unreachable = [c for c in cited if c not in producers]
        led["entries"]["T2_claim_reachability"].update(
            verdict=RESOLVED if not unreachable else RESOLVED,
            finding=("cited=%d, code-connected=%d, CLAIM_UNREACHABLE=%s"
                     % (len(cited), len(cited) - len(unreachable),
                        unreachable or "none")))

    # --- T3 doc currency ----------------------------------------------
    doc_edges = [e for e in by_kind.get("path_ref", [])
                 + by_kind.get("md_link", [])
                 if e["source"] in doc_files]
    if not doc_edges:
        led["entries"]["T3_doc_currency"].update(
            verdict="LINK_IS_NONE",
            reason="docs carry no file link edges; doc currency has no "
                   "doc-to-file surface to check staleness against",
            finding="docs name no files")
    else:
        stale = sorted({e["target"] for e in doc_edges
                        if e["resolvable"] is False})
        led["entries"]["T3_doc_currency"].update(
            verdict=RESOLVED,
            finding=("doc->file edges=%d, STALE(unresolvable)=%s"
                     % (len(doc_edges), stale or "none")))

    # --- T4 two-way ----------------------------------------------------
    fwd = {(e["source"], e["target"]) for e in by_kind.get("path_ref", [])}
    back_pairs = 0
    one_way = 0
    for s, t in fwd:
        t_base = os.path.basename(t)
        match = [f for f in files if f == t or os.path.basename(f) == t_base]
        if not match:
            continue
        back = any(e2["source"] in match and
                   (e2["target"] == s or os.path.basename(e2["target"])
                    == os.path.basename(s))
                   for e2 in by_kind.get("path_ref", []))
        if back:
            back_pairs += 1
        else:
            one_way += 1
    if not fwd:
        led["entries"]["T4_two_way"].update(
            verdict="LINK_IS_NONE",
            reason="no path_ref edges at all; two-way linkage has no "
                   "link surface to measure direction on",
            finding="no file references anywhere")
    else:
        led["entries"]["T4_two_way"].update(
            verdict=RESOLVED,
            finding=("forward links with resolvable targets checked; "
                     "two-way=%d, one-way=%d" % (back_pairs, one_way)))

    # --- T5 situation declared ----------------------------------------
    sit_hits = [e for e in by_kind.get("path_ref", [])
                + by_kind.get("md_link", [])
                if "situation" in e["target"].lower()
                or "situation" in e["source"].lower()]
    if not doc_files:
        led["entries"]["T5_situation_declared"].update(
            verdict="INSTRUMENT_BLIND",
            reason="the scan reads link syntax, not session intent; "
                   "with no doc surface the situation the artifact is "
                   "for is invisible to this instrument",
            finding="no doc files in scan")
    elif sit_hits:
        led["entries"]["T5_situation_declared"].update(
            verdict=RESOLVED,
            finding="situation surface linked: %d edge(s) naming "
                    "situations" % len(sit_hits))
    else:
        led["entries"]["T5_situation_declared"].update(
            verdict=RESOLVED,
            finding="docs exist but no situation link surface detected "
                    "in the scan -- situation undeclared on the link "
                    "surface, which is the part this instrument measures")

    # --- T6 absence named ----------------------------------------------
    refused = [mv for mv, e in led["entries"].items()
               if e.get("verdict") in REFUSALS]
    if refused:
        led["entries"]["T6_absence_named"].update(
            verdict=RESOLVED,
            finding="absences present and named as first-class cells: "
                    + ", ".join(refused))
    else:
        led["entries"]["T6_absence_named"].update(
            verdict=RESOLVED,
            finding="no absence cells arose in this run; the refusal "
                    "path is exercised by the suite, not asserted here")

    return led


def render(led, sc):
    out = []
    out.append("tool_use_audit -- %s" % led.get("artifact", "?"))
    out.append("=" * 70)
    for mv, meta in MOVES.items():
        e = led["entries"][mv]
        s = sc["per_move"][mv]
        mark = {None: "  --", 0.0: " 0.0", 1.0: " 1.0"}[s]
        out.append("%s %s  %-22s %-16s %s"
                   % (mark, mv, meta["measurand"],
                      e.get("verdict") or "NOT_RUN",
                      (e.get("finding") or "")[:60]))
    out.append("-" * 70)
    out.append("score %.1f of %.1f   scored %d   refusal_fraction %s"
               % (sc["total"], sc["possible"], sc["scored"],
                  ("%.2f" % sc["refusal_fraction"])
                  if sc["refusal_fraction"] is not None else "--"))
    if sc["moves_not_run"]:
        out.append("moves_not_run: %s" % sc["moves_not_run"])
    return "\n".join(out)


def main(argv):
    if "--emit" in argv:
        name = argv[argv.index("--emit") + 1]
        print(json.dumps({"moves": MOVES,
                          "blank_ledger": blank_ledger(name)}, indent=2))
        return 0
    if "--scan" in argv:
        with open(argv[argv.index("--scan") + 1]) as fh:
            scan = json.load(fh)
        led = audit_from_scan(scan)
        sc = score(led)
        print(render(led, sc))
        if "--out" in argv:
            with open(argv[argv.index("--out") + 1], "w") as fh:
                json.dump(led, fh, indent=2)
        return 0
    if "--ledger" in argv:
        with open(argv[argv.index("--ledger") + 1]) as fh:
            led = json.load(fh)
        print(render(led, score(led)))
        return 0
    if "--paths" in argv:
        idx = argv.index("--paths")
        ledgers = []
        for p in argv[idx + 1:]:
            if p.startswith("--"):
                break
            with open(p) as fh:
                ledgers.append(json.load(fh))
        print(json.dumps(path_independence(ledgers), indent=2))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
