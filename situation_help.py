#!/usr/bin/env python3
# situation_help.py -- CC0, stdlib only, no network, phone-buildable.
#
# Situation -> candidate instruments IN THIS REPO, or SITUATION_UNMAPPED.
#
# A situation with no instrument is a RETURN TYPE, not an error, and it
# is never replaced by a nearest guess. The registry's coverage is the
# measurement; the situation is only the sample. An unmapped situation
# is a finding about the repo -- it says what this repo cannot help
# with -- and it is printed in the FIRST line of output, before
# anything else, so the user learns the repo cannot help before
# investing in the details. That is the fullness test: help that hides
# its absence is half help.
#
# THE LIMIT, STATED HERE RATHER THAN AT THE BOTTOM
#     Matching is a word list over situation signatures. A situation
#     described in words outside every signature maps to nothing, and
#     that zero is a property of THE REGISTRY, never evidence that the
#     situation is unusual or unimportant. Paraphrase steps around the
#     list; the suite shows one doing so.
#
# usage:  python3 situation_help.py LIST
#         python3 situation_help.py "my repo's README lies about files"
#         python3 situation_help.py --file situations/mine.txt

import os
import re
import sys

# ---------------------------------------------------------------------
# Situation signatures. Each signature is a list of word-boundary
# patterns; a situation matches when ANY pattern fires. Signatures name
# instruments in THIS repo only -- this module cannot point outside the
# tree and does not pretend to.
# ---------------------------------------------------------------------

SIGNATURES = {
    "undocumented_or_phantom_tools": {
        "patterns": [
            r"readme (lies|wrong|stale|out of date)",
            r"files? (that|it names)? ?(don'?t|do not) exist",
            r"phantom (file|tool|script|command)",
            r"what (tools?|scripts?) (do i|does this) (have|actually)",
            r"dead (link|command|reference)",
            r"which (scripts?|files?) (are|is) (real|the real)",
            r"abandoned drafts?",
            r"inherited (a|this|the) repo",
            r"entry points?",
        ],
        "instruments": ["crosslink_scan.py", "tool_use_audit.py (T1, T3)"],
    },
    "claims_disconnected_from_code": {
        "patterns": [
            r"claims? (not |un)?(connected|backed|recomputable)",
            r"claims? and the code",
            r"numbers? (i|we|nobody) can'?t (recompute|trace|reproduce|find)",
            r"where does this (number|figure|value) come from",
            r"assertion[s]? (with|and) no (test|check|source)",
            r"headline (figure|number|metric)",
            r"can'?t find the code",
            r"nobody can find",
            r"disconnected",
        ],
        "instruments": ["tool_use_audit.py (T2)",
                        "crosslink_scan.py (cites_claim edges)"],
    },
    "no_stated_purpose": {
        "patterns": [
            r"(don'?t|do not) know what (this|it) (is for|does)",
            r"what situation",
            r"who is this for",
            r"no (readme|docs?|description)",
            r"purpose (is )?(unclear|unknown|unstated)",
        ],
        "instruments": ["tool_use_audit.py (T5)",
                        "situation_help.py (this module, reflexively)"],
    },
    "audit_wont_run_in_order": {
        "patterns": [
            r"steps? (must|have to) (be |)run in order",
            r"order[- ]dependent",
            r"path[- ]dependent",
            r"same (result|answer) every order",
        ],
        "instruments": ["tool_use_audit.py (--paths falsifier)"],
    },
    "help_is_one_way": {
        "patterns": [
            r"docs? (point|link) (to|at) code but not back",
            r"one[- ]way (link|help|docs?)",
            r"can'?t get back to the docs?",
            r"help (is |feels |)half",
        ],
        "instruments": ["tool_use_audit.py (T4)"],
    },
}

SITUATION_UNMAPPED = "SITUATION_UNMAPPED"


def _match(text):
    text = text.lower()
    hits = []
    for name, sig in SIGNATURES.items():
        for pat in sig["patterns"]:
            if re.search(pat, text):
                hits.append(name)
                break
    return hits


def help_for(situation_text):
    """Return (status, lines). status is SITUATION_UNMAPPED or MAPPED."""
    hits = _match(situation_text)
    if not hits:
        return SITUATION_UNMAPPED, [
            SITUATION_UNMAPPED
            + " -- this repo has no instrument for that situation, and "
              "no nearest guess is offered.",
            "The registry's coverage is the measurement; the situation",
            "is the sample. A zero here is a property of the registry.",
        ]
    lines = ["MAPPED -- %d situation signature(s) fired:" % len(hits)]
    for h in hits:
        lines.append("  %s" % h)
        for inst in SIGNATURES[h]["instruments"]:
            lines.append("      -> %s" % inst)
    lines.append("")
    lines.append("Each instrument listed is a file IN THIS REPO. Run it;")
    lines.append("the help is the code, and the code is crosslinked from")
    lines.append("the README, which is the two-way condition T4 checks.")
    return "MAPPED", lines


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    if argv[1] == "LIST":
        print("registered situation signatures: %d" % len(SIGNATURES))
        for name, sig in SIGNATURES.items():
            print("  %-32s -> %s" % (name, ", ".join(sig["instruments"])))
        print("")
        print("a situation outside every signature returns "
              + SITUATION_UNMAPPED + ", first line, no nearest guess.")
        return 0
    if argv[1] == "--file":
        with open(argv[2], encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    else:
        text = " ".join(argv[1:])
    status, lines = help_for(text)
    print("\n".join(lines))
    return 0 if status == "MAPPED" else 3  # unmapped exits nonzero,
                                           # but with the answer printed
                                           # FIRST -- absence is data


if __name__ == "__main__":
    sys.exit(main(sys.argv))
