# Coding-agent log: Jinja issue 2069

Agent: **Claude Code** (Claude Opus 5.5) in VS Code, working in this repository.
Task: the HW3 handout (`hw3.pdf`) was given to the agent as its sole
specification, with a request to carry out the assignment end to end. No
hints about the bug, the relevant files or the fix were provided; every step
below was chosen by the agent.
Evidence files are in `evidence/`.

## 1. Exploring the repository and the issue

| Step | What the agent did | Result |
|---|---|---|
| 1 | Cloned `pallets/jinja`, checked out tag `3.1.6`, created a venv with an editable install. | `jinja2.__version__ == "3.1.6"` |
| 2 | Read **only the issue body** (`gh issue view 2069 --json title,body`), not its comments or linked pull requests, to avoid seeing an existing fix. | Expected `{'control'}`, got `{'control', 'output'}`. The reporter says this is a regression between 3.1.4 and 3.1.5 and suspects the fix for issue 1253. |
| 3 | Ran the issue example as a script. | Reproduced: `['control', 'output']` |
| 4 | Read `meta.py`. | `TrackingCodeGenerator.enter_frame` reports every symbol whose load action is `"resolve"`, so the question is why `output` gets a resolve load. That symbol tracking is in `idtracking.py`. |
| 5 | `git log 3.1.4..3.1.6 -- idtracking.py compiler.py meta.py`, then `git show 66587ce9` (the issue 1253 change that shipped in 3.1.5). | The commit removed a shortcut in `Symbols.branch_update`: "skip names stored in all 3 branches". Its regression test reads `a.b` **before** `set a` in one branch. |

The agent did not read the whole codebase. It went from the issue, to `meta.py`,
to `idtracking.py`, then to the git history of those files, and only opened
`compiler.py` and `parser.py` to check how `If` nodes are compiled and parsed.

## 2. Root cause

Instead of reasoning from the code alone, the agent dumped the symbol tables
(`Symbols.analyze_node`) for four templates on both 3.1.4 and 3.1.6 (script
in the session transcript):

| Template | 3.1.4 | 3.1.6 |
|---|---|---|
| if/elif/else, all set `output` | `undefined` (correct) | `resolve` (**bug**) |
| if/else, both set `output` | `resolve` (**also wrong**) | `resolve` (**wrong**) |
| issue 1253: read before set in one branch | `undefined` (**wrong**) | `resolve` (correct) |
| if without else | `resolve` (correct) | `resolve` (correct) |

This showed that restoring 3.1.4's behaviour would not be a general fix:
3.1.4 only "worked" when there were exactly three branches. `visit_If`
always passes `[body, elif, else]`, so a plain if/else counts its empty elif
placeholder as a branch that does not assign.

The agent then compared `idtracking.visit_If` with `Parser.parse_if` and
`CodeGenerator.visit_If`. The parser and compiler treat `elif_` as a flat
list of `(test, body)` clauses that share the outer `else`. `idtracking`
visited **all** elif clauses together in **one** branch copy, each as a full
`If` with an empty `else`, so each one looked like an `if` without `else`.

**Root cause.** `branch_update` decides whether a name stored in an `if`
still needs its outer (context) value. 3.1.4 approximated this as "stored in
all three branches"; 3.1.5 replaced that with "always". The correct condition
is: the outer value is needed only if some branch does not store the name, or
some branch reads it before storing it. And `elif` must be modelled as
separate branches for "every branch" to mean anything.

Before patching, the agent also checked Jinja's existing straight-line
semantics (evidence in the session): a direct read before `set` resolves
from the context, while a read from a nested scope (loop body, `{% set %}`
block) before a later `set` gives *undefined*. It flagged that the obvious
fix might change rendering for nested-scope reads.

## 3. Patches

**Reproduction test first.** It was added to `tests/test_api.py::TestMeta`
and committed on its own. Baseline run: 909 passed, 1 failed (the new test).
Evidence: `01`, `02`.

**Patch v1** (`branch_update` checks "every branch stores the name and its
load in that branch is not resolve"; `visit_If` gives each elif its own
branch). Result: **910 passed**, including the reproduction test, the issue
1253 test and the existing `test_idtracking` if-branch tests. By the test
suite alone, this patch looked finished.

**Differential check, written by the agent** (`scripts/differential.py`):
it renders 3,030 templates under the original 3.1.6 and the patch. Result:
**2 templates rendered differently** (evidence `03-differential-patch-v1.txt`):

```
{% for i in [1] %}{{ x }}{% endfor %}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}
    3.1.6='CTX1'  patched='1'
```

A loop body is analyzed as a separate scope, so its read of `x` is not
recorded in the outer frame's symbols, and patch v1 skipped the lookup the
loop still needed. The agent had predicted this risk before writing v1, but
shipped v1 first and only caught it through differential testing. Jinja's
existing 910 tests did not catch it.

**Patch v2.** `FrameSymbolVisitor` records names that a nested scope (for,
macro, call block, filter block, with, set block, scope, overlay scope) loads
before the frame stores them (`Symbols.nested_loads`), and `branch_update`
treats those like direct reads. `Block` is left out on purpose: block bodies
read from the context, not from frame locals (checked by the differential).
Result: 0 rendering differences, 940 tests passing.

Evidence `03-patch-v1-against-final-tests.txt` shows the final test suite
fails on patch v1 (**6 failures**), so the regression is now covered by
tests.

## 4. Mistakes the agent made and fixed

| Mistake | How it was caught |
|---|---|
| Patch v1 changed rendering for nested-scope reads (above). | Differential testing against the original 3.1.6 |
| A hand-written corpus template was invalid syntax (`{% call(v) dict(a=1).items %}`). Both versions raised the same `TemplateSyntaxError`, so the differential counted it as "no difference" and it silently tested nothing. | The oracle script crashed on it; then every corpus template was checked to parse |
| The first oracle used only string values, so `{% set x = x + 1 %}` raised the same `TypeError` for both values, and `x` was wrongly counted as "never affects output". | Inspecting the examples behind the over-report count; added a numeric value pair |
| A shortcut that `exec`'d half of `differential.py` to reuse its templates failed (that script reads `sys.argv` at import). | Error; moved the corpus to `templates.py` |
| Evidence capture produced empty files: under zsh, an unquoted `$NEW` holding several test paths is not word-split. | The evidence files were empty; reran with explicit paths |
| Patch v2's first helper failed `mypy` (`find_all((Name, NSRef))` is typed as `Expr`, which has no `.name`). New tests had 5 lines over ruff's 88-column limit. | Ran the repo's configured ruff and mypy; mypy errors compared against unmodified 3.1.6 to tell new from pre-existing |
| Commit messages contained `#2069` / `#1253`, which GitHub can turn into backlinks on the real upstream issues. | Reviewed before pushing; reworded as "issue 2069" |
| The first README (a) gave a `pytest -k` filter that selects 36 tests while promising the 40 in the evidence, and (b) installed only `pytest`. In a fresh environment the full suite then errors, because `test_async*.py` need `trio`; the agent's own venv had `trio` installed earlier, which hid the problem. | Following the README literally in a fresh clone; now uses explicit test IDs and `requirements/tests.in` |

## 5. Validation summary

| Check | Original 3.1.6 | Patch v1 | Final patch |
|---|---|---|---|
| Reproduction test | fails | passes | passes |
| New + related tests (40) | 13 fail / 27 pass | 6 fail | all pass |
| Full Jinja suite | 909 pass (+1 new failing) | 910 pass | **940 pass** |
| Differential: templates rendering differently (of 3,038) | | 2 (of 3,030) | **0** (sync and async) |
| Oracle: false negatives | 0 | | **0** |
| Oracle: over-reports | 233 | | 216 |
| ruff / mypy on changed files | | | clean |
| Python versions | | | 3.9.6 and 3.14.7 |

## 6. Review-driven refinement (directed by the student)

After the work was declared complete and the repository published, the
student asked the agent for a **strict assessment against the handout**,
then directed it to address every weakness that assessment found. This was
the main human intervention in the process.

| Weakness found in review | Action | Result |
|---|---|---|
| Compile-time overhead of 20 to 30% on deeply nested templates | Profiled with `cProfile`: `_note_nested_loads` walked each nested scope's subtree twice (separate `find_all` passes for `Name` and `NSRef`) | Single pass. Overhead on the worst case dropped from +55 ms (+21%) to +27 ms (+10%); flat templates unchanged. A per-node cache could remove the rest, but was judged not worth the added complexity for a one-time, cached cost. |
| Only the default (sync) code generator compared | Added `--async` to `differential.py` (`enable_async=True`) | 0 rendering differences in async mode too (`evidence/10-differential-async.txt`) |
| Only tested on Python 3.14 | Ran the suite, the before/after tests and the differential on macOS's system Python 3.9.6 | Identical results (`evidence/11-python39.txt`). This also exposed a **README bug**: Python 3.9's bundled pip cannot install this `pyproject.toml` project in editable mode, so the README now upgrades pip first. |
| README and report listed four commits after 3.1.6; there were five | Commit table updated | |

