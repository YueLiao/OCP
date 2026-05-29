"""Predefined SAT/MILP constraint builders."""

from tools import sat_cardinality
from tools import search_constraints


def expand_constraint_vars(cons_vars, bitwise=True):
    cons_vars_name = []
    for var in cons_vars:
        if isinstance(var, str):
            cons_vars_name.append(var)
        elif bitwise and var.bitsize > 1:
            cons_vars_name.extend(f"{var.ID}_{j}" for j in range(var.bitsize))
        else:
            cons_vars_name.append(var.ID)
    return cons_vars_name


def gen_predefined_constraints(
    model_type,
    cons_type,
    cons_vars,
    cons_value,
    bitwise=True,
    encoding=None,
    pysat_available=lambda: sat_cardinality.pysat_import,
    require_cardenc=sat_cardinality.require_pysat_cardenc,
    cardinality_constraints=sat_cardinality.pysat_cardinality_constraints,
):
    """
    Generate commonly used, predefined model constraints based on type and parameters.

    Args:
        cons_type (str): The constraint type, must be one of the predefined types:
            - "EXACTLY": All selected variables == a target value.
            - "AT_LEAST": All selected variables >= target value.
            - "AT_MOST": All selected variables <= target value.
            - "SUM_EXACTLY": Sum of selected variables == target value.
            - "SUM_AT_LEAST": Sum of selected variables >= target value.
            - "SUM_AT_MOST": Sum of selected variables <= target value.
        cons_vars (list): Variable names or Variables objects with ID and bitsize attributes.
        cons_value (int): Target value.
        bitwise (bool): If True, expand variables by bit.

    Returns:
        list[str]: List of generated model constraint strings.
    """
    builders = {
        "EXACTLY": gen_constraints_exactly,
        "SUM_EXACTLY": gen_constraints_sum_exactly,
        "AT_MOST": gen_constraints_at_most,
        "SUM_AT_MOST": gen_constraints_sum_at_most,
        "AT_LEAST": gen_constraints_at_least,
        "SUM_AT_LEAST": gen_constraints_sum_at_least,
    }
    if cons_type not in builders:
        raise ValueError(f"Unsupported cons_type '{cons_type}'.")

    cons_vars_name = expand_constraint_vars(cons_vars, bitwise=bitwise)
    return builders[cons_type](
        model_type,
        cons_vars_name,
        cons_value,
        encoding=encoding,
        pysat_available=pysat_available,
        require_cardenc=require_cardenc,
        cardinality_constraints=cardinality_constraints,
    )


def gen_constraints_exactly(
    model_type,
    cons_vars,
    cons_value,
    encoding=None,
    pysat_available=None,
    require_cardenc=None,
    cardinality_constraints=None,
):
    if model_type == "milp":
        return [f"{cons_vars[i]} = {cons_value}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 0:
        return [f"-{cons_vars[i]}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 1:
        return [f"{cons_vars[i]}" for i in range(len(cons_vars))]
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for EXACTLY constraint.")


def gen_constraints_sum_exactly(
    model_type,
    cons_vars,
    cons_value,
    encoding=1,
    pysat_available=lambda: sat_cardinality.pysat_import,
    require_cardenc=sat_cardinality.require_pysat_cardenc,
    cardinality_constraints=sat_cardinality.pysat_cardinality_constraints,
):
    if model_type == "milp":
        return [' + '.join(f"{cons_vars[i]}" for i in range(len(cons_vars))) + f" = {cons_value}"]
    elif model_type == "sat" and cons_value == 0:
        return [f"-{cons_vars[i]}" for i in range(len(cons_vars))]
    elif model_type == "sat" and pysat_available():
        if not encoding:
            encoding = 1  # Default to 1 if not specified
        assert encoding in [0,1,2,3,4,5,6,7,8,9], (
            f"[ERROR] Invalid encoding = {encoding}, refer "
            "https://pysathq.github.io/docs/html/api/card.html"
        )
        card_enc = require_cardenc()
        return cardinality_constraints(cons_vars, cons_value, encoding, card_enc.equals, "equals")
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for SUM_EXACTLY constraint.")


def gen_constraints_at_most(
    model_type,
    cons_vars,
    cons_value,
    encoding=None,
    pysat_available=None,
    require_cardenc=None,
    cardinality_constraints=None,
):
    if model_type == "milp":
        return [f"{cons_vars[i]} <= {cons_value}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 0:
        return [f"-{cons_vars[i]}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 1:
        return []
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for AT_MOST constraint.")


def gen_constraints_sum_at_most(
    model_type,
    cons_vars,
    cons_value,
    encoding="SEQUENTIAL",
    pysat_available=lambda: sat_cardinality.pysat_import,
    require_cardenc=sat_cardinality.require_pysat_cardenc,
    cardinality_constraints=sat_cardinality.pysat_cardinality_constraints,
):
    if model_type == "milp":
        return [' + '.join(f"{cons_vars[i]}" for i in range(len(cons_vars))) + f" <= {cons_value}"]
    elif model_type == "sat" and (encoding == "SEQUENTIAL" or encoding is None):
        return search_constraints.gen_sequential_encoding_sat(cons_vars, cons_value)
    elif model_type == "sat" and pysat_available():
        if not isinstance(encoding, int):
            encoding = 1  # Default to 1 if the encoding is not specified as an integer
        card_enc = require_cardenc()
        return cardinality_constraints(cons_vars, cons_value, encoding, card_enc.atmost, "atmost")
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for SUM_AT_MOST constraint.")


def gen_constraints_at_least(
    model_type,
    cons_vars,
    cons_value,
    encoding=None,
    pysat_available=None,
    require_cardenc=None,
    cardinality_constraints=None,
):
    if model_type == "milp":
        return [f"{cons_vars[i]} >= {cons_value}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 1:
        return [f"{cons_vars[i]}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 0:
        return []
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for GREATER_EQUAL constraint.")


def gen_constraints_sum_at_least(
    model_type,
    cons_vars,
    cons_value,
    encoding=1,
    pysat_available=lambda: sat_cardinality.pysat_import,
    require_cardenc=sat_cardinality.require_pysat_cardenc,
    cardinality_constraints=sat_cardinality.pysat_cardinality_constraints,
):
    if model_type == "milp":
        return [' + '.join(f"{cons_vars[i]}" for i in range(len(cons_vars))) + f" >= {cons_value}"]
    elif model_type == "sat" and cons_value == 1:
        return [' '.join(f"{cons_vars[i]}" for i in range(len(cons_vars)))]
    elif model_type == "sat" and pysat_available():
        card_enc = require_cardenc()
        return cardinality_constraints(cons_vars, cons_value, encoding, card_enc.atleast, "atleast")
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for SUM_GREATER_EQUAL constraint.")
