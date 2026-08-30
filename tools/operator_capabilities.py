"""Operator capability introspection.

Each Operator subclass declares its capability surface:
  - ``SUPPORTED_MODEL_VERSIONS``: a ``{model_type: version suffixes}`` map giving the versions
    its ``generate_model`` accepts under each model_type (a version may be MILP-only, e.g.
    INTEGRAL_TWOSUBSET, or ModAdd's indicator-constraint XORDIFF_1/2/3).
  - ``SUPPORTED_IMPLEMENTATIONS``: the languages its ``generate_implementation``
    supports (defaults to python/c/verilog on the base class).

``describe_operators()`` reads those declarations (the single source of truth, e.g.
for the agent to answer "what does operator X support?"). ``extract_from_source()``
statically re-derives the model versions from the code with ``ast``; ``consistency_report()``
diffs the two so a declaration cannot silently drift from the code.
"""

import ast
import importlib
from pathlib import Path

OPERATORS_DIR = Path(__file__).resolve().parent.parent / "operators"

_OPERATOR_MODULES = (
    "operators.operators",
    "operators.boolean_operators",
    "operators.modular_operators",
    "operators.matrix",
    "operators.Sbox",
    "operators.AESround",
    "operators.SHACAL2BooleanFunctions",
)

# AST static extraction over-reports these (a shared helper references the version
# but a runtime guard excludes this operator). Documented so consistency stays green.
_AST_OVERREPORTS = set()

# Composite operators propagate the round-level version to their inner operators instead
# of referencing each version literally, so AST extraction cannot see these declarations.
# They are validated at runtime (check_supported_model_version) and by the inner operators
# the composite delegates to, so they are legitimately "declared but not in source".
_DELEGATED_VERSIONS = {
    ("AESround", version)
    for version in (
        "XORDIFF", "XORDIFF_A", "XORDIFF_PR",
        "LINEAR", "LINEAR_A", "LINEAR_PR",
        "TRUNCATEDDIFF", "TRUNCATEDDIFF_A",
        "TRUNCATEDLINEAR", "TRUNCATEDLINEAR_A",
    )
}


# --------------------------- declaration reading (runtime) ---------------------------

def _load_all():
    for module in _OPERATOR_MODULES:
        importlib.import_module(module)


def describe_operators():
    """Return {operator: {module, model_versions, implementations}} from declarations.

    Lists only classes that DECLARE ``SUPPORTED_MODEL_VERSIONS`` themselves (concrete
    subclasses that merely inherit, e.g. every named S-box inheriting ``Sbox``, are
    represented by their declaring base).
    """
    _load_all()
    from operators.operators import Operator

    result = {}
    stack = list(Operator.__subclasses__())
    seen = set()
    while stack:
        cls = stack.pop()
        if cls in seen:
            continue
        seen.add(cls)
        stack.extend(cls.__subclasses__())
        if "SUPPORTED_MODEL_VERSIONS" in cls.__dict__:
            declaration = cls.__dict__["SUPPORTED_MODEL_VERSIONS"]
            result[cls.__name__] = {
                "module": cls.__module__.split(".")[-1] + ".py",
                # {model_type: [version suffixes]} -- a version may be supported under milp but not sat
                "model_versions": {model_type: list(versions) for model_type, versions in declaration.items()},
                "implementations": list(getattr(cls, "SUPPORTED_IMPLEMENTATIONS", ())),
            }
    return dict(sorted(result.items()))


# --------------------------- static extraction (ast cross-check) ---------------------------

def _model_version_suffixes(node):
    suffixes = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.Add):
            left, right = sub.left, sub.right
            if isinstance(right, ast.Constant) and isinstance(right.value, str) and right.value.startswith("_"):
                is_class_name = (
                    (isinstance(left, ast.Attribute) and left.attr == "__name__")
                    or (isinstance(left, ast.Name) and left.id == "class_name")
                )
                if is_class_name:
                    suffixes.add(right.value[1:])
    return suffixes


def _called_module_funcs(node, module_funcs):
    return {
        sub.func.id
        for sub in ast.walk(node)
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name) and sub.func.id in module_funcs
    }


def extract_from_source():
    """Return {operator: set(model_version_suffixes)} statically parsed from generate_model."""
    result = {}
    for path in sorted(OPERATORS_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(path.read_text())
        module_funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            gm = next((m for m in cls.body if isinstance(m, ast.FunctionDef) and m.name == "generate_model"), None)
            if gm is None:
                continue
            versions = _model_version_suffixes(gm)
            for fname in _called_module_funcs(gm, module_funcs):
                versions |= _model_version_suffixes(module_funcs[fname])
            if versions:
                result[cls.name] = versions
    return result


def consistency_report():
    """Diff declarations against static extraction; return {operator: {missing, extra}}.

    ``missing``: versions the code handles but that are NOT declared (real drift to fix).
    ``extra``  : versions declared but not seen statically (usually fine, e.g. inheritance).
    Documented AST over-reports are ignored.
    """
    # Cross-check the union of all model types' versions against the statically-parsed set
    # (the sat/milp split itself is not AST-verified, only that every version is declared).
    declared = {
        name: set().union(*(set(versions) for versions in info["model_versions"].values()))
        for name, info in describe_operators().items()
    }
    extracted = extract_from_source()
    report = {}
    for name, decl in declared.items():
        ast_versions = extracted.get(name, set()) - {v for (op, v) in _AST_OVERREPORTS if op == name}
        missing = ast_versions - decl
        extra = decl - extracted.get(name, set()) - {v for (op, v) in _DELEGATED_VERSIONS if op == name}
        if missing or extra:
            report[name] = {"missing": sorted(missing), "extra": sorted(extra)}
    return report


if __name__ == "__main__":
    for name, info in describe_operators().items():
        print(f"{name}  ({info['module']})")
        for model_type, versions in info["model_versions"].items():
            print(f"    model_versions[{model_type}] : {', '.join(versions) or '-'}")
        print(f"    implementations : {', '.join(info['implementations']) or '-'}")
    rep = consistency_report()
    print("\nconsistency:", "OK" if not rep else rep)
