# CS 59300 Homework 3: fixing pallets/jinja issue 2069

This repository is Jinja **3.1.6** with a fix for
[pallets/jinja issue 2069](https://github.com/pallets/jinja/issues/2069):
`meta.find_undeclared_variables()` reports a variable as undeclared even when
it is set in every branch of an `{% if %}` / `{% elif %}` / `{% else %}` block.

```python
from jinja2 import Environment, meta

ast = Environment().parse(
    "{% if control == 'something' %}{% set output = 1 %}"
    "{% elif control == 'something else' %}{% set output = 2 %}"
    "{% else %}{% set output = 3 %}{% endif %}{{ output }}"
)
meta.find_undeclared_variables(ast)
# Jinja 3.1.6: {'control', 'output'}   (wrong)
# this fix:    {'control'}
```

## What changed

The history starts at the unmodified release commit, so every change is visible:

| Commit | Content |
|---|---|
| `15206881` (tag `3.1.6`) | Original Jinja 3.1.6, unmodified |
| `Add failing test reproducing issue 2069` | The reproduction test only. It **fails** at this commit. |
| `Don't report variables set in all if branches as undeclared` | The fix: `src/jinja2/idtracking.py` and a `CHANGES.rst` entry |
| `Add tests for variables set in if branches` | Additional validation tests |
| `Add HW3 README, scripts and evidence` | This folder |
| `Reword task description in AGENT_LOG` | Documentation only |
| `Scan nested scopes in a single pass` | Performance refinement of the fix (behavior unchanged) |
| `Update HW3 docs and evidence after review` | Documentation, scripts and evidence for the refinement |
| `Clarify that the oracle is a test over the corpus, not a proof` | Wording in `scripts/oracle.py` |

See the whole patch with `git diff 3.1.6 -- src/` (one file, `src/jinja2/idtracking.py`).

**Root cause, briefly.** `find_undeclared_variables` reports every name that the
compiler's symbol tracking (`idtracking.py`) marks as *resolve*, meaning "look
it up in the template context". When an `if` block stores a name,
`Symbols.branch_update` decides whether the name still needs that lookup.
Jinja 3.1.5 (the fix for issue 1253) made it *always* do the lookup. Before
that, 3.1.4 skipped it when the name was stored in three branches, which was
wrong if a branch read the name first, and also wrong for a plain `if/else`.
`FrameSymbolVisitor.visit_If` also analyzed all `elif` clauses together as
nested `if`s with no `else`, unlike the parser and compiler. The fix skips the
lookup only when **every** branch stores the name **before** anything reads it,
including reads from nested scopes such as loops and macros. It also treats
each `elif` as its own branch.

## Set up

Requires Python 3.9+ and git. Tested on Python **3.9.6** and **3.14.7**.

```bash
git clone https://github.com/Yash-11-star/jinja-hw3-issue-2069.git jinja-hw3
cd jinja-hw3
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip         # older pips can't install pyproject.toml projects in editable mode
pip install -e . -r requirements/tests.in   # Jinja's test dependencies: pytest, trio
```

## Reproduce the original failure

Check out the commit that adds only the reproduction test (the source is still
unmodified 3.1.6), and run the test:

```bash
git checkout "$(git log --format=%h --grep='Add failing test reproducing issue 2069')"
pytest tests/test_api.py -k undeclared -v
```

Expected: `test_find_undeclared_variables_set_in_all_if_branches` **FAILS** with
`AssertionError: assert {'control', 'output'} == {'control'}`.

To run **all** of the new tests against the original source, check out the
latest commit and swap in the original `src/` temporarily:

```bash
git checkout main
git checkout 3.1.6 -- src/jinja2/idtracking.py
pytest -v tests/test_api.py::TestMeta tests/test_idtracking.py \
    tests/test_regression.py::test_load_parameter_when_set_in_all_if_branches \
    tests/test_regression.py::test_set_in_all_if_branches_render
git checkout main -- src/jinja2/idtracking.py      # restore the fix
```

Expected on the original source: **13 failed, 27 passed** (40 tests: the new
tests plus the existing `TestMeta`, `test_idtracking` and issue 1253 tests). The 13 failures
are the cases where the variable is set on every path. The 27 that pass are
guard tests that must keep passing: partial assignment, read before set, reads
from nested scopes, and rendering.

## Run the tests with the fix

```bash
git checkout main
# The reproduction test, the new tests and the related existing ones
pytest -v tests/test_api.py::TestMeta tests/test_idtracking.py \
    tests/test_regression.py::test_load_parameter_when_set_in_all_if_branches \
    tests/test_regression.py::test_set_in_all_if_branches_render
# Jinja's full test suite (regression check)
pytest
```

Expected: all 40 selected tests pass, and the full suite passes (**940 passed**).

| Where | New tests |
|---|---|
| `tests/test_api.py::TestMeta` | `test_find_undeclared_variables_set_in_all_if_branches` (reproduction) and `test_find_undeclared_variables_if_branches` (24 cases) |
| `tests/test_regression.py` | `test_set_in_all_if_branches_render` (5 cases): rendering is unchanged |
| `tests/test_idtracking.py` | `test_if_branching_stores_all_branches`, `test_if_branching_stores_all_branches_load_first`: symbol tables |

## Extra verification scripts (optional)

These compare the fix against the original 3.1.6 on many templates. They need a
second checkout of the original source:

```bash
git worktree add /tmp/jinja-3.1.6 3.1.6

# Render 3,038 templates (38 hand-written + 3,000 random if/elif/else chains)
# under both versions with 8 contexts; report any difference.
python hw3/scripts/differential.py /tmp/jinja-3.1.6/src
python hw3/scripts/differential.py /tmp/jinja-3.1.6/src --async    # enable_async=True
#   expected (both): different rendering: 0, different find_undeclared_variables: 20

# Check that every variable whose context value can change the output is
# still reported (no false negatives).
python hw3/scripts/oracle.py
#   expected: false negatives: 0

# Compile-time cost of the fix
PYTHONPATH=/tmp/jinja-3.1.6/src python hw3/scripts/benchmark.py
python hw3/scripts/benchmark.py
```

## Contents of this folder

- `evidence/`: saved output of every step (failing test before the fix, the
  baseline suite, the first patch's regression, differential, oracle and
  benchmark results).
- `scripts/`: `differential.py`, `oracle.py`, `templates.py` (the template
  corpus) and `benchmark.py`.
- `AGENT_LOG.md`: how the coding agent investigated and fixed the bug.
