# WORK ORDER -- vibe-code-audit, delivered verbatim

```
repo:    vibe-code-audit
license: CC0, stdlib only, no network, phone-buildable

BUILD: three instruments over one artifact class.

ARTIFACT CLASS: a vibe-coded codebase. Code produced fast,
through an assistant, intent carried in session. The
crosslinks are the spec that survives the session.

INSTRUMENT 1 -- crosslink_scan.py
  Pull the crosslinks. For every file in the tree:
    path references       a/b/c.py, ./x, ../y
    imports               import x / from x import y
    backticked commands   `python3 foo.py --bar`
    markdown links        [text](target)
    claim-id citations    two or more uppercase letters,
                          underscore, digits  (VCA_001 style)
  Emit an EDGE LEDGER as JSON. Every edge carries:
    source file, target, kind, line, resolvable flag.
  A target that does not exist in the tree is extracted
  and marked resolvable: false. Never dropped. Never
  resolved silently.

INSTRUMENT 2 -- tool_use_audit.py
  The audit. Four measurands, all read off the edge
  ledger, none off the prose:
    TOOL        what instruments exist -- and are they
                declared, runnable, or phantom
    TOOL_USE    are tools connected to claims -- every
                numbered claim reachable from an entry
                point, or CLAIM_UNREACHABLE
    SITUATION   does the artifact name the situation it
                is for -- edge vs detected, or neither
    HELP_FULL   is help FULL: reachable, current,
                claim-connected, two-way
  Scoring rule (build it in): a correctly-refused
  verdict scores as high as a correct one. Absence
  moves must be selectable. LINK_IS_NONE is a finding
  about the artifact, not a failure of the audit.
  Ship a falsifier for move path-independence.

INSTRUMENT 3 -- situation_help.py
  Given a situation (free text, or LIST to enumerate),
  return the candidate instruments IN THIS REPO, or
  SITUATION_UNMAPPED. A situation with no instrument is
  a return type, not an error. Never a nearest guess.

  FULLNESS TEST, built in: for the situation the user
  actually brought, if the returned set is empty the
  output must say so in the first line -- the user
  learns the repo cannot help BEFORE reading anything
  else.

CLAIM TABLE: VCA_ ids, permanent, each with a falsifier.
TEST SUITE: AST guards (locate-only enforcement),
planted faults, null tests. Prints the count.
```
