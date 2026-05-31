"""Objective-target parsing and objective constraint builders."""

import tools.model_objective as model_objective
from tools.predefined_constraints import gen_predefined_constraints
from tools.search_constraints import gen_matsui_constraints_sat


def parse_objective_target(objective_target):
    if objective_target == "OPTIMAL" or objective_target == "EXISTENCE":
        return objective_target, None
    for keyword in ["AT MOST", "EXACTLY", "AT LEAST"]:
        if objective_target.startswith(keyword):
            try:
                value = float(objective_target.split()[-1])
                return keyword, value
            except ValueError:
                raise ValueError(f"Invalid format: '{objective_target}'. Expected '{keyword} X'.")
    raise ValueError(f"Unsupported objective_target: {objective_target}")


def gen_milp_constraints_from_objective_target(objective_target):
    """Generate MILP constraints from an objective target string."""
    strategy, value = parse_objective_target(objective_target)
    if strategy == "AT MOST":
        return gen_predefined_constraints("milp", "AT_MOST", ["obj"], value)
    if strategy == "EXACTLY":
        return gen_predefined_constraints("milp", "EXACTLY", ["obj"], value)
    if strategy == "AT LEAST":
        return gen_predefined_constraints("milp", "AT_LEAST", ["obj"], value)
    return []


def _sat_objective_encoding(config_model, cons_type):
    if cons_type == "SUM_AT_MOST":
        return config_model.get("atmost_encoding_sat", "SEQUENTIAL")
    if cons_type == "SUM_EXACTLY":
        return config_model.get("exact_encoding_sat", 1)
    if cons_type == "SUM_AT_LEAST":
        return config_model.get("atleast_encoding_sat", 1)
    return None


def gen_sat_constraints_from_objective_target(
    objective_function,
    config_model,
    cons_type,
    obj_val,
    obj_val_decimal=None,
    log=None,
):
    """Generate SAT constraints induced by an objective target."""
    encoding = _sat_objective_encoding(config_model, cons_type)
    if encoding is None:
        return []

    constraints = []
    if obj_val_decimal is not None:
        obj_fun_vars, obj_fun_vars_decimal = model_objective.gen_obj_fun_variables(
            objective_function,
            obj_fun_decimal=True,
        )
        assert len(obj_val_decimal) == len(obj_fun_vars_decimal), (
            "Length mismatch between objective function decimal variables and obj_val_decimal."
        )
        for i in range(len(obj_fun_vars_decimal)):
            hw_list = [obj for row in obj_fun_vars_decimal[i] for obj in row]
            constraints += gen_predefined_constraints(
                "sat",
                cons_type,
                hw_list,
                obj_val_decimal[i],
                encoding=encoding,
            )
    else:
        obj_fun_vars = model_objective.gen_obj_fun_variables(
            objective_function,
            obj_fun_decimal=False,
        )

    if "matsui_constraint" in config_model and obj_val > 0:
        if log is not None:
            log("[INFO] Applying Matsui constraints for SAT modeling.", config_model)
        assert cons_type == "SUM_AT_MOST", "Matsui constraints only support 'AT MOST' objective target."
        Round = config_model.get("matsui_constraint").get("Round")
        best_obj = config_model.get("matsui_constraint").get("best_obj")
        GroupConstraintChoice = config_model["matsui_constraint"].get("GroupConstraintChoice", 1)
        GroupNumForChoice = config_model["matsui_constraint"].get("GroupNumForChoice", 1)
        if Round is None or best_obj is None:
            raise ValueError("[WARNING] Please provide 'Round' and 'best_obj' for Matsui strategy.")
        if obj_val >= best_obj[-1]:
            constraints += gen_matsui_constraints_sat(
                Round,
                best_obj,
                obj_val,
                obj_fun_vars,
                GroupConstraintChoice,
                GroupNumForChoice,
            )
        else:
            if log is not None:
                log(
                    f"[WARNING] Skipping Matsui constraints since obj_val = {obj_val} < best_obj[-1] = {best_obj[-1]}.",
                    config_model,
                )
            hw_list = [obj for row in obj_fun_vars for obj in row]
            constraints += gen_predefined_constraints(
                "sat",
                cons_type,
                hw_list,
                obj_val,
                encoding=encoding,
            )
    else:
        hw_list = [obj for row in obj_fun_vars for obj in row]
        constraints += gen_predefined_constraints(
            "sat",
            cons_type,
            hw_list,
            obj_val,
            encoding=encoding,
        )
    return constraints
