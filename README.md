# vibe-code-audit

An audit harness for **vibe-coded** codebases -- codebases produced fast,
through an assistant, with the operator carrying intent in session rather
than in writing. The premise: in such a codebase, the **crosslinks** are
often the only durable specification there is. READMEs link to files,
files import files, docs cite commands, commands name outputs. Pull those
links and you can audit things the prose never states.

CC0. Python 3 standard library only. No network. Parses under 3.9.
Phone-buildable.

```
python3 crosslink_scan.py PATH ...        extract crosslinks -> edge ledger (JSON)
python3 tool_use_audit.py --scan FILE     audit a codebase from its edge ledger
python3 tool_use_audit.py --ledger FILE   audit a filled ledger
python3 tool_use_audit.py --emit "name"   print the move set and a blank ledger
python3 situation_help.py LIST            situation -> candidate instruments
python3 situation_help.py "text..."       locate the situation in free text
python3 test_audit.py                     the checks; prints their count
```

---

## The four measurands

The audit measures four things, each from the crosslink graph, none from
the prose's self-description:

| measurand | question | graph signature |
|---|---|---|
| **TOOL** | what instruments does this codebase actually have? | `entry_point` edges: declared, runnable, or phantom |
| **TOOL_USE** | are the tools connected to the claims? | every numbered claim reachable from an entry point via `produces` edges |
| **SITUATION** | does the artifact know which situation it is for? | `declares_situation` edges vs. situations detected in the docs |
| **HELP_FULL** | is help FULL -- reachable, current, and two-way? | docs coverage of files; back-links from files to docs; edge freshness |

**FULL** is a measurand, not a compliment. Help is FULL for a tool when
four conditions hold: the tool is reachable from the documentation surface,
the documentation for it is current against the code it names, the tool's
claims are connected to something that can recompute them, and the link
runs both ways (doc names file, file names doc). Each condition is checked
against the edge ledger, and each can fail alone.

## The scoring rule this repo exists for

**A correctly-refused verdict scores as high as a correct one.** Five
refusal verdicts -- `NOT_DERIVABLE`, `NOT_SEPARABLE`, `NOT_ADDRESSABLE`,
`LINK_IS_NONE`, `INSTRUMENT_BLIND` -- score 1.0 exactly as `RESOLVED`
does, and `refusal_fraction` is reported, never penalized. A vibe-coded
artifact with no crosslinks is not a zero; it is a ledger full of
`LINK_IS_NONE`, which is a **finding about the artifact**, not a failure
of the audit. Evals that score answers only never select for the absence
moves.

## The limit, stated here rather than at the bottom

`crosslink_scan.py` is a **syntax walker**. It finds links that are
written down: paths, imports, backticked commands, markdown links,
citations of claim IDs. A link that lives only in the operator's head --
"I know `audit.py` is the real one" -- is invisible to it, and the size of
that invisible set is not measurable from inside the scan. So
`LINK_IS_NONE` is a property of THE ARTIFACT AS SHIPPED, never evidence
that no understanding exists. The artifact's link surface is the
measurement; the codebase is only the sample.

A second limit: the scan cannot tell a true link from a dead one by
existence alone for anything it cannot open (URLs, network references).
Those edges are extracted and marked `resolvable: False` -- counted,
never resolved silently and never dropped silently.

## Files

```
crosslink_scan.py     extract crosslinks (paths, imports, commands,
                      markdown links, claim-id citations) -> edge ledger
tool_use_audit.py     the audit: four measurands, move set, scorer,
                      falsifier for path-independence
situation_help.py     situation registry: map a described situation to
                      the candidate instruments IN THIS REPO, or
                      SITUATION_UNMAPPED -- never a nearest guess
test_audit.py         the checks. AST guards, planted faults, null tests
ledgers/              filled audit ledgers (demos)
samples/              pinned outputs
situations/           shipped situation descriptions for situation_help
WORK_ORDER.md         the order this was built to, verbatim
CLAIM_TABLE.md        VCA_001..VCA_016 with falsifiers
```

Siblings in the lineage this scaffold borrows from: the move-set /
refusal-scoring pattern, the claim-table-with-falsifiers pattern, the
locate-only lexical pattern, and the checker-never-edits-the-entry
pattern, all from `github.com/JinnZ2/Simulators`.

CC0.
