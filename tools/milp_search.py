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
def _milp_objective_function(objective_target, objective_function):
    if objective_target == "EXISTENCE":
        return None
    return objective_function[:]


def _build_milp_model_constraints(objective_target, constraints, objective_function, config_model):
    model_cons = list(constraints or [])
    model_cons.extend(gen_milp_constraints_from_objective_target(objective_target))

    matsui_config = config_model.get("matsui_constraint")
    if matsui_config is None:
        return model_cons

    Round = matsui_config.get("Round")
    best_obj = matsui_config.get("best_obj")
    cons_type = matsui_config.get("matsui_milp_cons_type", "ALL")
    if Round is None or best_obj is None or len(best_obj) != (Round - 1):
        raise ValueError("Must provide correct 'Round' and 'best_obj' for Matsui strategy.")
    model_cons.extend(gen_matsui_constraints_milp(Round, best_obj, objective_function, cons_type))
    return model_cons


def _attach_milp_solution_objectives(solutions, objective_function):
    for sol in solutions:
        round_values = model_objective.cal_round_obj_fun_values_from_solution(objective_function, sol)
        sol["rounds_obj_fun_values"] = round_values
        if "obj_fun_value" not in sol or sol["obj_fun_value"] == 0:
            sol["obj_fun_value"] = sum(round_values)


def modeling_solving_milp(objective_target, constraints, objective_function, config_model, config_solver): # Construct and solve the MILP model.
    # Step 1. Generate model constraints.
    model_cons = _build_milp_model_constraints(objective_target, constraints, objective_function, config_model)

    # Step 3. Generate the standard MILP model.
    obj_fun = _milp_objective_function(objective_target, objective_function)
    write_milp_model(model_cons, obj_fun, config_model.get("filename"))

    # Step 4. Solve the MILP model.
    solutions = solving.solve_milp(config_model.get("filename"), config_solver)
    _attach_milp_solution_objectives(solutions, objective_function)

    # Step 5. Print modeling and solving information.
    log_search_summary(
        "Modeling and Solving MILP Information",
        solutions,
        config_model,
        config_solver,
        hidden_keys={"positions"},
    )
    return solutions
