"""Anti-pattern audit.

Verifies, by static AST analysis, that the agentic loop does NOT:
- use string-membership tests against text content to drive control flow
- use an integer-literal iteration cap as its primary stopping mechanism
- omit reference to `stop_reason` as the loop-breaking signal

And that the package broadly does not branch on `claim_type` equality
outside of the tool-schema definitions and the cost-estimate module.

Each test parses the relevant file with `ast` and walks the tree. There are
no runtime imports of claims_intake here — the audit is static, so it works
even if loop.py / tools.py do not run end-to-end.
"""

from __future__ import annotations

import ast
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "claims_intake"
LOOP_PY = PKG / "loop.py"


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


# ---------------------------------------------------------------------------
# Anti-pattern 1 — no string-membership tests against assistant text in the loop
# ---------------------------------------------------------------------------
def test_no_string_membership_against_text_in_loop() -> None:
    """No `"some_token" in <something>` expressions in loop.py.

    Heuristic: any `ast.Compare` node using `ast.In` whose `left` operand is a
    string `ast.Constant` is flagged. The loop has no legitimate reason to test
    for the presence of a magic string inside the model's output — that would be
    natural-language-driven control flow.
    """
    tree = ast.parse(LOOP_PY.read_text())
    offenders: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Compare):
            for op in node.ops:
                if (
                    any(isinstance(op, ast.In) for op in node.ops)
                    and isinstance(node.left, ast.Constant)
                    and isinstance(node.left.value, str)
                ):
                    offenders.append(ast.unparse(node))

    assert not offenders, (
        "Found string-membership tests in loop.py:" + " , ".join(offenders)
    )
# ---------------------------------------------------------------------------
# Anti-pattern 2 — no integer-literal iteration cap as the primary stop mechanism
# ---------------------------------------------------------------------------
def test_no_integer_literal_iteration_cap_in_loop() -> None:
    """No `for _ in range(<int literal>)` and no `while <var> < <int literal>` in loop.py.

    Token/wall-clock/config-sourced budgets are explicitly allowed because they
    read their cap from a `Budget` instance (an attribute access or a function
    arg), not from a literal. If you need a cap, pass it in.
    """
    tree = ast.parse(LOOP_PY.read_text())
    offenders: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            if (
                isinstance(node.iter, ast.Call)
                and isinstance(node.iter.func, ast.Name)
                and node.iter.func.id == "range"
                and any(
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, int)
                    for arg in node.iter.args
                )
            ):
                offenders.append(ast.unparse(node))

        if isinstance(node, ast.While):
            if(
                isinstance(node.test, ast.Compare)
                and any(
                    isinstance(comparator, ast.Constant)
                    and isinstance(comparator.value, int)
                    for comparator in node.test.comparators
                )
            ):
                offenders.append(ast.unparse(node))

    assert not offenders, (
        "Found integer-literal iteration cap in loop.py; use a Budget instead: "
        + ", ".join(offenders)
    )

# ---------------------------------------------------------------------------
# Positive evidence — stop_reason is the value that breaks the while loop
# ---------------------------------------------------------------------------
def test_stop_reason_is_loop_control() -> None:
    """loop.py references `stop_reason` AND a `while` loop exits via return/raise on it."""
    tree = ast.parse(LOOP_PY.read_text())

    has_stop_reason_reference = any(
        (
            isinstance(node, ast.Attribute)
            and node.attr == "stop_reason"
        )
        or (
            isinstance(node, ast.Name)
            and node.id == "stop_reason"
        )
        for node in ast.walk(tree)
    )

    assert has_stop_reason_reference, (
        "loop.py must reference `stop_reason` as the loop-breaking signal."
    )

    while_exits_on_stop_reason = False
    for node in ast.walk(tree):
        if isinstance(node, ast.While):
            body_text = "\n".join(
                ast.unparse(statement) for statement in node.body
            )
            if (
                "stop_reason" in body_text
                and (
                    "return" in body_text
                    or "raise" in body_text
                    )
            ):
                while_exits_on_stop_reason = True
                break
    assert while_exits_on_stop_reason, (
        "At least one `while` loop in loop.py must exit via `return` or `raise` on `stop_reason`."
    )

# ---------------------------------------------------------------------------
# Decision-tree-in-Python — no `if claim_type == "..."` branches in the package
# ---------------------------------------------------------------------------
def test_no_claim_type_equality_branching_in_package() -> None:
    """Decision logic about claim type lives in the model, not in Python.

    tools.py is exempt (it defines the enum in input_schema).
    pricing.py is exempt (it may map claim_type to per-queue cost weights).
    """
    offenders: list[str] = []
    exempt_files = {"tools.py", "pricing.py", "__init__.py"}

    for python_file in PKG.rglob("*.py"):
        if python_file.name in exempt_files:
            continue

        tree = ast.parse(python_file.read_text())

        for node in ast.walk(tree):
            if not isinstance(node, ast.Compare):
                continue

            has_equality_operator = any(
                isinstance(op, ast.Eq) for op in node.ops
            )

            left_is_claim_type = (
                isinstance(node.left, ast.Name)
                and node.left.id == "claim_type"
            ) or (
                isinstance(node.left, ast.Attribute)
                and node.left.attr == "claim_type"
            )

            compared_to_string = any(
                isinstance(comparator, ast.Constant)
                and isinstance(comparator.value, str)
                for comparator in node.comparators
            )

            if (
                has_equality_operator
                and left_is_claim_type
                and compared_to_string
            ):
                relative_path = python_file.relative_to(PKG)
                offenders.append(
                    f"{relative_path}:{node.lineno}: {ast.unparse(node)}"
                )

    assert not offenders, (
        "Found decision-tree branching on `claim_type` in the package. Move the decision into the model via tool calls: "
        + "\n".join(offenders)
    )
