"""PySAT cardinality backend helpers used by model constraint generation."""

from importlib import import_module
from importlib.util import find_spec
import warnings


CardEnc = None
vpool = None
pysat_import = find_spec("pysat") is not None


def load_pysat_cardinality_backend():
    global CardEnc, pysat_import, vpool

    if CardEnc is not None and vpool is not None:
        return CardEnc, vpool
    try:
        CardEnc = import_module("pysat.card").CardEnc
        IDPool = import_module("pysat.formula").IDPool
    except ImportError:
        pysat_import = False
        return None, None
    vpool = IDPool(start_from=1000)
    pysat_import = True
    return CardEnc, vpool


def require_pysat_cardenc():
    card_enc, _ = load_pysat_cardinality_backend()
    if card_enc is None:
        raise ValueError("PySAT is required for SAT cardinality constraints.")
    return card_enc


def pysat_cardinality_error_types():
    try:
        card_module = import_module("pysat.card")
    except ImportError:
        return (ValueError, RuntimeError)
    return tuple(
        error_type
        for error_type in (
            getattr(card_module, "NoSuchEncodingError", None),
            getattr(card_module, "UnsupportedBound", None),
            ValueError,
            RuntimeError,
        )
        if error_type is not None
    )


def readable_cardinality_clauses(cnf, reverse_map):
    readable_clauses = []
    for clause in cnf.clauses:
        readable = " ".join(
            f"-{reverse_map.get(abs(lit), f'dummy_{abs(lit)}')}"
            if lit < 0
            else reverse_map.get(abs(lit), f"dummy_{abs(lit)}")
            for lit in clause
        )
        readable_clauses.append(readable)
    return readable_clauses


def pysat_cardinality_constraints(
    cons_vars,
    cons_value,
    encoding,
    encoder,
    encoder_name,
    backend_loader=load_pysat_cardinality_backend,
    error_types_loader=pysat_cardinality_error_types,
):
    if not encoding:
        encoding = 1
    _, card_vpool = backend_loader()
    if card_vpool is None:
        raise ValueError("PySAT is required for SAT cardinality constraints.")
    variable_map = {name: idx + 1 for idx, name in enumerate(cons_vars)}
    reverse_map = {v: k for k, v in variable_map.items()}
    lits = [variable_map[name] for name in cons_vars]
    try:
        cnf = encoder(lits=lits, bound=cons_value, vpool=card_vpool, encoding=encoding)
    except error_types_loader():
        warnings.warn(
            f"CardEnc.{encoder_name} does not support encoding {encoding}; no constraints generated.",
            RuntimeWarning,
        )
        return []
    return readable_cardinality_clauses(cnf, reverse_map)
