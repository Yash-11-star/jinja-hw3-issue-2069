"""Compile-time benchmark for the patch (run once per Jinja version).

Builds templates with many if/elif/else blocks and deeply nested loops, and
reports the median time of Environment.parse + find_undeclared_variables and
of a full compile.
Usage: python hw3/scripts/benchmark.py
"""

import statistics
import time

import jinja2
from jinja2 import Environment
from jinja2 import meta

IF_BLOCK = (
    "{% if c == 1 %}{% set x = 1 %}{% elif c == 2 %}{% set x = 2 %}"
    "{% else %}{% set x = 3 %}{% endif %}{{ x }}"
)


def nested(depth):
    open_ = "".join(f"{{% for i{d} in s %}}" + IF_BLOCK for d in range(depth))
    return open_ + "{{ x }}" + "{% endfor %}" * depth


CASES = {
    "flat: 500 if/elif/else blocks": IF_BLOCK * 500,
    "nested: 15 levels of for + if": nested(15),
    "nested: 8 levels x 50 copies": nested(8) * 50,
}

env = Environment()
print(f"jinja2 from {jinja2.__file__}")
for name, src in CASES.items():
    meta_t, compile_t = [], []
    for _ in range(7):
        t0 = time.perf_counter()
        meta.find_undeclared_variables(env.parse(src))
        meta_t.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        env.compile(src)
        compile_t.append(time.perf_counter() - t0)
    print(
        f"{name:34} meta {statistics.median(meta_t) * 1000:8.1f} ms"
        f"   compile {statistics.median(compile_t) * 1000:8.1f} ms"
    )
