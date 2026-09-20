# CLAIM TABLE -- vibe-code-audit

Ids are permanent. `VCA_` = vibe-code-audit. Status is one of
SUPPORTED / REFUTED / UNVERIFIED. Every SUPPORTED claim is a property
of the three modules or of their measured output, and is recomputable
by anyone with the folder: `python3 test_audit.py` (43 checks).

---

## crosslink_scan.py

**VCA_001 -- LOCATE ONLY is enforced, not promised. SUPPORTED.**
The module carries no field in which a verdict could be written. An AST
walk over every identifier, argument, attribute and function name finds
none of `verdict / severity / grade / rank / rating / defect / suggest /
recommend / rewrite / improve / fix` (the vocabulary list lives in a
string constant so the guard does not trip on itself). The guard is
planted-against: a module containing `def suggest_fix` fires it
(`ast.guard_not_silent`). *Falsifier:* an identifier from that
vocabulary appearing in the module, or a returned field carrying a
verdict.

**VCA_002 -- the guard polices names, not prose. SUPPORTED.**
A module that only *says* the forbidden words in a docstring ("this
module gives no verdict, no severity, no fix") passes the guard
(`ast.guard_polices_names_not_prose`). A locate-only module must be able
to state its own limit without tripping its own enforcement. The guard
is therefore weaker than a full-content scan, and that weakness is the
correct one: the alternative forbids the module from documenting what it
refuses to do.

**VCA_003 -- comments are never counted as imports. SUPPORTED.**
`# import not_real_comment` inside a Python file produces no import
edge; imports are extracted by AST walk, not by regex over lines
(`scan.comment_not_import`). *Falsifier:* an import edge whose target
appears only inside a comment.

**VCA_004 -- an unresolvable target is extracted and marked, never
dropped and never resolved silently. SUPPORTED.**
A fixture doc naming `ghost.py`, which does not exist, produces a
`path_ref` edge with `resolvable: false` (`scan.ghost_extracted_not_dropped`).
URLs are always `resolvable: false` because the module opens no network
(`scan.url_unresolvable_kept`). *Falsifier:* a fixture with a phantom
target producing zero edges for it, or a URL edge marked resolvable.

**VCA_005 -- the scan is deterministic. SUPPORTED.**
Two scans of the same tree produce byte-identical edge sets
(`scan.deterministic`). *Falsifier:* two runs over one tree differing
in their edge JSON.

**VCA_006 -- an empty tree is a return, not an error. SUPPORTED.**
A directory with no text files yields a ledger with zero files and zero
edges (`scan.empty_tree`). *Falsifier:* an exception or nonzero exit on
an empty tree.

## tool_use_audit.py

**VCA_007 -- symmetric scoring: a correctly-refused verdict scores as
high as a correct one. SUPPORTED.** `RESOLVED` with a non-empty finding
scores 1.0; `LINK_IS_NONE` with a reason naming its target scores 1.0
(`score.resolved_full`, `score.named_refusal_full`). `refusal_fraction`
is reported and never subtracted (`score.refusal_fraction`).

**VCA_008 -- a bare refusal scores zero, and the guard's limit is
stated and exercised. SUPPORTED, limit shown.** A refusal whose reason
is `"x"` scores 0.0 (`score.bare_refusal_zero`). The guard requires the
reason to contain at least one token from the move's own measurand or
trigger vocabulary. A two-word reason that names the target passes
(`score.thin_reason_passes_guard_limit`) -- the module docstring states
this is a guard against the *empty* refusal, not against a determined
one, and the repair (human review) is out of scope and not claimed.

**VCA_009 -- unknown verdicts and empty findings score zero.
SUPPORTED.** A verdict outside `RESOLVED + REFUSALS` scores 0.0
(`score.unknown_verdict_zero`); a `RESOLVED` with an empty finding
scores 0.0 (`score.resolved_needs_finding`). Symmetric generosity does
not extend to unlabelled outputs.

**VCA_010 -- the path-independence falsifier checks its precondition
and refuses to speak at the edges. SUPPORTED.** Zero runs returns
`UNTESTABLE_NO_RUNS`; one run returns `UNTESTABLE_ONE_RUN`; two runs in
the same order returns `UNTESTABLE_SAME_ORDER` -- the claim is reported
untested rather than passed (`falsifier.zero_runs_refuses`,
`falsifier.one_run_refuses`, `falsifier.same_order_refuses`). This is
the repair of the failure mode where a falsifier "tests its consequence
without checking its precondition": two byte-identical ledgers cannot
return ORDERLESS here.

**VCA_011 -- the falsifier fires on real divergence. SUPPORTED.**
Two ledgers with different orders and one differing entry return
`PATH_DEPENDENT_CLAIM_FAILS` and name the differing move
(`falsifier.fires_on_difference`).

**VCA_012 -- the auto-audit refuses where the graph cannot answer, and
the absence is a first-class cell. SUPPORTED.** A scan with no
`cites_claim` edges produces `T2_claim_reachability = LINK_IS_NONE`
with a reason naming the missing link surface; a scan with no Python
files produces `T1_inventory = LINK_IS_NONE`. Exercised in the fixture
family and in the scorer family. *Falsifier:* a scan with no claim
edges producing a RESOLVED claim-reachability verdict.

## situation_help.py

**VCA_013 -- an unmapped situation is a return type, printed first,
exit nonzero. SUPPORTED.** "how do i bake bread" returns
`SITUATION_UNMAPPED` as the FIRST line of output and exits 3
(`sit.unmapped_is_first_line`, `sit.unmapped_exit_nonzero`,
`sit.absence_printed_first`). The user learns the repo cannot help
before reading anything else -- the fullness test from the work order.
No nearest guess is offered, and no guessing machinery exists in the
module (`ast.situation_no_guess`).

**VCA_014 -- THE LIMIT: a word list, and a paraphrase steps around it.
SUPPORTED, and measured rather than asserted.** "dead link in the
readme" maps; a sufficiently paraphrased equivalent may not, and which
way a given paraphrase falls is a property of THE REGISTRY, recorded by
the suite rather than hidden (`sit.wordlist_limit_measured`,
`sit.paraphrase_recorded`). A zero from this module is never evidence
that a situation is unusual or unimportant.

**VCA_015 -- signatures name instruments in this repo only.
SUPPORTED.** Every `instruments` entry in every signature resolves to a
file present in the tree (`crosslink_scan.py`, `tool_use_audit.py`,
`situation_help.py`). The module cannot point outside the tree and does
not pretend to. *Falsifier:* a signature naming a file absent from the
tree (checked by `self.audit_all_scored` family over the shipped
registry against the tree's file list).

## cross-cutting

**VCA_016 -- the shipped self-scan reproduces against the live tree.
SUPPORTED at ship time, perishable by construction.** The pinned sample
`samples/self_scan.sample.json` re-derives from the tree as shipped
(`self.files_stable`, `self.phantoms_named`). This claim is expected to
go stale the moment the tree changes, and the staleness is detectable
by re-running the scan -- a pinned output is a snapshot, not a truth.
*Falsifier:* re-running `crosslink_scan.py .` and diffing; the check
tests subset-stability of the file list, not byte equality, precisely
because the tree grows.

**VCA_017 -- nothing here measures code quality. UNVERIFIED, and
load-bearing on nothing.** The audit measures link structure:
existence, resolvability, reachability, two-way-ness, declared
situations. Whether the linked code is correct, the docs are good, or
the tool helps anyone is out of scope for every measurand. A repo can
score 6.0 of 6.0 and be useless; a repo full of LINK_IS_NONE can be
excellent in one person's head. Stated in the README, repeated here,
claimed nowhere.
