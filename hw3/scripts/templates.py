"""Template corpus shared by differential.py and oracle.py.

Hand-written cases for if/elif/else assignment plus 3,000 randomly generated
if/elif/else chains (fixed seed, so the corpus is the same on every run).
"""

import random

HAND_WRITTEN = [
    # issue #2069 and variants
    "{% if c == 1 %}{% set x = 1 %}{% elif c == 2 %}{% set x = 2 %}{% else %}{% set x = 3 %}{% endif %}{{ x }}",
    "{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% if c %}{% set x = 1 %}{% endif %}{{ x }}",
    "{% if c %}{% set x = 1 %}{% elif d %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% if c %}{% set x = 1 %}{% elif d %}{% else %}{% set x = 3 %}{% endif %}{{ x }}",
    # #1253: read before set in one branch
    "{% if c %}{{ x }}{% set x = 1 %}{% elif d %}{% set x = 2 %}{% else %}{% set x = 3 %}{% endif %}{{ x }}",
    "{% if c %}{% set x = 1 %}{% else %}{{ x }}{% set x = 2 %}{% endif %}{{ x }}",
    "{% if c %}{% set x = x + 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    # read in an elif test before the branch sets it
    "{% if c %}{% set x = 1 %}{% elif x %}{% set x = 2 %}{% else %}{% set x = 3 %}{% endif %}{{ x }}",
    # read before / set before the if
    "{{ x }}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% set x = 0 %}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    # nested ifs
    "{% if c %}{% if d %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{% else %}{% set x = 3 %}{% endif %}{{ x }}",
    "{% if c %}{% if d %}{% set x = 1 %}{% endif %}{% else %}{% set x = 3 %}{% endif %}{{ x }}",
    "{% if c %}{% set x = 1 %}{% else %}{% if d %}{% set x = 2 %}{% else %}{% set x = 3 %}{% endif %}{% endif %}{{ x }}",
    # other ways of assigning in a branch
    "{% if c %}{% set x %}A{% endset %}{% else %}{% set x %}B{% endset %}{% endif %}{{ x }}",
    "{% if c %}{% macro x() %}A{% endmacro %}{% else %}{% macro x() %}B{% endmacro %}{% endif %}{{ x() }}",
    "{% if c %}{% set x, y = 1, 2 %}{% else %}{% set x, y = 3, 4 %}{% endif %}{{ x }}{{ y }}",
    "{% if c %}{% set x = 1 %}{% set y = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}{{ y }}",
    # set inside a loop body does not leak out of the loop
    "{% if c %}{% for i in [1] %}{% set x = 1 %}{% endfor %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    # inside loops, macros and blocks
    "{% for i in [1, 2] %}{% if c %}{% set x = i %}{% else %}{% set x = 0 %}{% endif %}{{ x }}{% endfor %}",
    "{% for i in [1, 2] %}{% if loop.first %}{% set x = i %}{% else %}{% set x = 0 %}{% endif %}{{ x }}{% endfor %}{{ x }}",
    "{% set x = 9 %}{% for i in [1] %}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}{% endfor %}{{ x }}",
    "{% macro m() %}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}{% endmacro %}{{ m() }}",
    "{% macro m(c) %}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}{% endmacro %}{{ m(c) }}{{ x }}",
    "{% with %}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}{% endwith %}{{ x }}",
    # inner scopes that read the name
    "{% if c %}{% for i in [1] %}{{ x }}{% endfor %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% if c %}{% set x = 1 %}{% for i in [1] %}{{ x }}{% endfor %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% for i in [1] %}{{ x }}{% endfor %}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% if c %}{% set y %}{{ x }}{% endset %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% macro m() %}{{ x }}{% endmacro %}{{ m() }}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}{{ m() }}",
    "{% macro w() %}{{ caller(1) }}{% endmacro %}{% if c %}{% call(v) w() %}{{ x }}{% endcall %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% filter upper %}{{ x }}{% endfilter %}{% if c %}{% set x = 'a' %}{% else %}{% set x = 'b' %}{% endif %}{{ x }}",
    "{% with v = 1 %}{{ x }}{% endwith %}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% set y %}{{ x }}{% endset %}{{ y }}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% block b %}{{ x }}{% endblock %}{% if c %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    "{% for i in [1] %}{% if c %}{% for j in [1] %}{{ x }}{% endfor %}{% set x = 1 %}{% else %}{% set x = 2 %}{% endif %}{{ x }}{% endfor %}",
    "{% if c %}{% set x = 1 %}{% set y %}{{ x }}{% endset %}{% else %}{% set x = 2 %}{% endif %}{{ x }}",
    # namespaces
    "{% set ns = namespace(v=0) %}{% if c %}{% set ns.v = 1 %}{% else %}{% set ns.v = 2 %}{% endif %}{{ ns.v }}",
]

# Randomly generated if/elif/else chains, nested up to depth 2.
STMTS = [
    "{% set x = 1 %}", "{{ x }}", "{% set x = x ~ 'a' %}", "", "{% set y = 1 %}", "{{ y }}",
    "{% for i in [1] %}{{ x }}{% endfor %}", "{% macro m() %}{{ y }}{% endmacro %}{{ m() }}",
]


def gen(rng, depth=0):
    parts = []
    for _ in range(rng.randint(0, 2)):
        if depth < 2 and rng.random() < 0.3:
            parts.append(gen_if(rng, depth + 1))
        else:
            parts.append(rng.choice(STMTS))
    return "".join(parts)


def gen_if(rng, depth):
    s = "{% if c %}" + gen(rng, depth)
    for _ in range(rng.randint(0, 2)):
        s += "{% elif " + rng.choice(["d", "x", "c"]) + " %}" + gen(rng, depth)
    if rng.random() < 0.6:
        s += "{% else %}" + gen(rng, depth)
    return s + "{% endif %}"


rng = random.Random(2069)
GENERATED = [gen(rng) + gen_if(rng, 1) + gen(rng) + "{{ x }}{{ y }}" for _ in range(3000)]
TEMPLATES = HAND_WRITTEN + GENERATED
