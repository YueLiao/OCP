import copy

import tools.model_objective as model_objective
from tools.model_io import write_milp_model
from tools.objective_targets import gen_milp_constraints_from_objective_target
from tools.search_constraints import gen_matsui_constraints_milp
from tools.search_reporting import log_search_summary
import solving.solving as solving


# **************************************************************************** #
# This module provides a interface for MILP-based modeling and solving for automated cryptanalysis, including:
# 1. Generate MILP constraints from the objective target.
# 2. Generate standard LP-format models.
# 3. Call the MILP solver (Gurobi, SCIP, etc.) to solve the model.
# **************************************************************************** #


# -------------------------- MILP Model Writing ---------------------------
# ------------------------ Modeling and Solving Interface ----------------------
def modeling_solving_milp(objective_target, constraints, objective_function, config_model, config_solver): # Construct and solve the MILP model.
    # Step 1. Generate model constraints
    model_cons = copy.deepcopy(constraints) or []
    model_cons += gen_milp_constraints_from_objective_target(objective_target)

    # Step 2: Add Matsui acceleration constraints ---
    if "matsui_constraint" in config_model:  # Arguments for Matsui branch-and-bound constraints. Example: config_model["matsui_constraint"] = {"Round": 2, "best_obj": [1], "matsui_milp_cons_type": "ALL"}.
        Round = config_model.get("matsui_constraint").get("Round")
        best_obj = config_model.get("matsui_constraint").get("best_obj")
        cons_type = config_model["matsui_constraint"].get("matsui_milp_cons_type", "ALL")
        if Round is None or best_obj is None or len(best_obj) != (Round-1):
            raise ValueError("Must provide correct 'Round' and 'best_obj' for Matsui strategy.")
        model_cons += gen_matsui_constraints_milp(Round, best_obj, objective_function, cons_type)

    # Step 3. Generate the standard MILP model.
    if objective_target == "EXISTENCE":
        obj_fun = None  # For existence checking, no objective function is needed.
    else:
        obj_fun = objective_function[:]
    write_milp_model(model_cons, obj_fun, config_model.get("filename"))

    # Step 4. Solve the MILP model.
    solutions = solving.solve_milp(config_model.get("filename"), config_solver)
    for sol in solutions:
        sol["rounds_obj_fun_values"] = model_objective.cal_round_obj_fun_values_from_solution(objective_function, sol)
        if "obj_fun_value" not in sol or sol["obj_fun_value"] == 0: sol["obj_fun_value"] = sum(sol["rounds_obj_fun_values"])

    # Step 5. Print modeling and solving information.
    log_search_summary(
        "Modeling and Solving MILP Information",
        solutions,
        config_model,
        config_solver,
        hidden_keys={"positions"},
    )
    return solutions
