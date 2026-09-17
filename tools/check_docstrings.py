"""Enforce Google-style docstrings on every function and method.

Ruff's pydocstyle rules check docstring layout but skip private functions and
never compare documented types with the signature. This checker covers every
function (public, private, nested) and requires:

- a docstring;
- an ``Args:`` entry ``name (type): description`` for each parameter except
  ``self``/``cls``, with ``type`` exactly matching the annotation, and no
  entries for parameters that do not exist;
- a ``Returns:`` section ``type: description`` matching the return annotation,
  unless the function returns ``None``.

``Annotated[T, ...]`` is documented as ``T``.

Usage: ``python tools/check_docstrings.py FILE [FILE ...]``.
"""

import ast
import re
import sys
from pathlib import Path

ARG_LINE = re.compile(r"^(\*{0,2}\w+) \((.+)\): \S")
RETURNS_LINE = re.compile(r"^(.+?): \S")
SECTION_HEADER = re.compile(r"^[A-Z][A-Za-z ]*:$")
IMPLICIT_PARAMS = {"self", "cls"}

Function = ast.FunctionDef | ast.AsyncFunctionDef


def annotation_text(annotation: ast.expr | None) -> str | None:
    """Render an annotation as source text, unwrapping ``Annotated[T, ...]`` to ``T``.

    Args:
        annotation (ast.expr | None): The annotation node, or None if absent.

    Returns:
        str | None: The annotation as source text, or None if there is no annotation.
    """
    if annotation is None:
        return None
    if (
        isinstance(annotation, ast.Subscript)
        and ast.unparse(annotation.value) in {"Annotated", "typing.Annotated"}
        and isinstance(annotation.slice, ast.Tuple)
    ):
        return ast.unparse(annotation.slice.elts[0])
    return ast.unparse(annotation)


def sections(docstring: str) -> dict[str, list[str]]:
    """Split a cleaned docstring into its Google-style sections.

    Args:
        docstring (str): Docstring text with common indentation removed.

    Returns:
        dict[str, list[str]]: Section name (e.g. ``"Args"``) mapped to the entry lines
            directly under it, dedented one level; continuation lines are dropped.
    """
    found: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in docstring.splitlines():
        if SECTION_HEADER.match(line):
            current = found.setdefault(line[:-1], [])
        elif current is not None and line.startswith("    ") and not line.startswith("     "):
            current.append(line[4:])
        elif current is not None and not line.strip():
            current = None
    return found


def parameters(node: Function) -> list[ast.arg]:
    """List a function's documentable parameters in signature order.

    Args:
        node (Function): The function definition.

    Returns:
        list[ast.arg]: Every parameter except ``self`` and ``cls``; ``*args`` and
            ``**kwargs`` are included with their stars restored in ``arg``.
    """
    spec = node.args
    params = [*spec.posonlyargs, *spec.args]
    if spec.vararg:
        params.append(ast.arg(arg=f"*{spec.vararg.arg}", annotation=spec.vararg.annotation))
    params.extend(spec.kwonlyargs)
    if spec.kwarg:
        params.append(ast.arg(arg=f"**{spec.kwarg.arg}", annotation=spec.kwarg.annotation))
    return [p for p in params if p.arg not in IMPLICIT_PARAMS]


def check_function(node: Function) -> list[str]:
    """Check one function's docstring against its signature.

    Args:
        node (Function): The function definition to check.

    Returns:
        list[str]: One message per problem found; empty if the docstring is valid.
    """
    docstring = ast.get_docstring(node)
    if docstring is None:
        return ["missing docstring"]

    found = sections(docstring)
    problems = []

    documented = {}
    for line in found.get("Args", []):
        match = ARG_LINE.match(line)
        if match is None:
            problems.append(f"Args entry must be 'name (type): description', got {line!r}")
        else:
            documented[match.group(1)] = match.group(2)

    params = parameters(node)
    for param in params:
        expected = annotation_text(param.annotation)
        if param.arg not in documented:
            problems.append(f"Args is missing '{param.arg} ({expected}): ...'")
        elif documented[param.arg] != expected:
            problems.append(
                f"Args type for '{param.arg}' is '{documented[param.arg]}', "
                f"annotation is '{expected}'"
            )
    for name in documented.keys() - {p.arg for p in params}:
        problems.append(f"Args documents '{name}', which is not a parameter")

    returns = annotation_text(node.returns)
    returns_lines = found.get("Returns", [])
    if returns not in {None, "None"}:
        match = RETURNS_LINE.match(returns_lines[0]) if returns_lines else None
        if match is None:
            problems.append(f"Returns section must start with '{returns}: description'")
        elif match.group(1) != returns:
            problems.append(f"Returns type is '{match.group(1)}', annotation is '{returns}'")
    return problems


def check_file(path: Path) -> list[str]:
    """Check every function in a Python file.

    Args:
        path (Path): The file to check.

    Returns:
        list[str]: ``path:line name: problem`` for each problem found.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        f"{path}:{node.lineno} {node.name}: {problem}"
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        for problem in check_function(node)
    ]


def main(argv: list[str]) -> int:
    """Check the files named on the command line and print every problem.

    Args:
        argv (list[str]): Paths of the Python files to check.

    Returns:
        int: Process exit code, 1 if any problem was found, otherwise 0.
    """
    problems = [p for arg in argv for p in check_file(Path(arg))]
    for problem in problems:
        print(problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
