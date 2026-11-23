"""Differential check: original Jinja 3.1.6 vs. the patched checkout.

Renders each template with several contexts under both versions and compares
the output, then compares find_undeclared_variables(). Prints every template
whose rendering or result differs.

Usage: python hw3/scripts/differential.py /path/to/original/jinja/src [--async]

With --async, both versions use Environment(enable_async=True), which
compiles templates to async code.
"""

import itertools
import json
import subprocess
import sys

from templates import GENERATED
from templates import HAND_WRITTEN
from templates import TEMPLATES

ORIGINAL_SRC = sys.argv[1]
ASYNC = "--async" in sys.argv[2:]

CONTEXTS = [dict(c=c, d=d, x="CTX", y="CY") for c, d in itertools.product([True, False], repeat=2)]
CONTEXTS += [dict(c=c, d=d) for c, d in itertools.product([True, False], repeat=2)]

RUNNER = r"""
import json, sys
sys.path.insert(0, sys.argv[1]) if sys.argv[1] != "-" else None
is_async = sys.argv[2] == "1"
from jinja2 import Environment, meta
templates, contexts = json.load(sys.stdin)
env = Environment(enable_async=is_async)
out = []
for src in templates:
    renders = []
    for ctx in contexts:
        try:
            renders.append(env.from_string(src).render(**ctx))
        except Exception as e:
            renders.append(f"<{type(e).__name__}: {e}>")
    try:
        undeclared = sorted(meta.find_undeclared_variables(env.parse(src)))
    except Exception as e:
        undeclared = f"<{type(e).__name__}>"
    out.append([renders, undeclared])
json.dump(out, sys.stdout)
"""


def run(src_path):
    proc = subprocess.run(
        [sys.executable, "-c", RUNNER, src_path, "1" if ASYNC else "0"],
        input=json.dumps([TEMPLATES, CONTEXTS]),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout)


old = run(ORIGINAL_SRC)
new = run("-")  # the installed (patched) checkout

render_diffs = meta_diffs = 0
for i, (src, (o_r, o_m), (n_r, n_m)) in enumerate(zip(TEMPLATES, old, new)):
    kind = "hand" if i < len(HAND_WRITTEN) else "gen"
    if o_r != n_r:
        render_diffs += 1
        print(f"RENDER DIFF [{kind}] {src}")
        for ctx, a, b in zip(CONTEXTS, o_r, n_r):
            if a != b:
                print(f"    {ctx}: 3.1.6={a!r} patched={b!r}")
    if o_m != n_m:
        meta_diffs += 1
        print(f"META   DIFF [{kind}] {src}\n    3.1.6={o_m} patched={n_m}")

print(f"\nmode: {'async' if ASYNC else 'sync'}")
print(f"{len(TEMPLATES)} templates ({len(HAND_WRITTEN)} hand-written, {len(GENERATED)} generated)"
      f" x {len(CONTEXTS)} contexts")
print(f"templates with different rendering: {render_diffs}")
print(f"templates with different find_undeclared_variables: {meta_diffs}")
