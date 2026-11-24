"""Dependency oracle for find_undeclared_variables on the patched checkout.

A name is *observably* read from the context if changing its value in the
render context changes the output for some combination of the conditions.
Every such name must be reported by find_undeclared_variables (otherwise the
fix hides a real dependency on the tested inputs; this is a test over the
corpus, not a proof). Names that are reported but never observable
are counted as remaining over-reports.

Uses the same templates as differential.py (templates.py).
Usage: python hw3/scripts/oracle.py
"""

import itertools
import sys

from templates import TEMPLATES

from jinja2 import Environment
from jinja2 import meta

env = Environment()


def render(template, **ctx):
    # A render error is an observable outcome too.
    try:
        return template.render(**ctx)
    except Exception as e:
        return f"<{type(e).__name__}: {e}>"


NAMES = ["x", "y"]
CONDITIONS = [dict(c=c, d=d) for c, d in itertools.product([True, False], repeat=2)]

# Two pairs of values, so that a name used as a number (x + 1) and as a
# string (x ~ 'a') both get a chance to change the output.
VALUE_PAIRS = [("CTX", "OTHER"), (1, 2)]


def is_observable(template, name):
    for cond, (v1, v2) in itertools.product(CONDITIONS, VALUE_PAIRS):
        others = {n: v1 for n in NAMES if n != name}
        if render(template, **cond, **others, **{name: v1}) != render(
            template, **cond, **others, **{name: v2}
        ):
            return True
    return False


missed = []
over = 0
for tpl in TEMPLATES:
    reported = meta.find_undeclared_variables(env.parse(tpl))
    template = env.from_string(tpl)
    for name in NAMES:
        observable = is_observable(template, name)
        if observable and name not in reported:
            missed.append((tpl, name))
        elif not observable and name in reported:
            over += 1

print(f"{len(TEMPLATES)} templates checked for names {NAMES}")
print(f"observable names NOT reported (false negatives): {len(missed)}")
for tpl, name in missed[:20]:
    print(f"    {name!r} in {tpl}")
print(f"reported names that never affect the output (over-reports): {over}")
sys.exit(1 if missed else 0)
