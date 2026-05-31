import tools.model_objective as model_objective
from tools.model_io import create_numerical_cnf, write_sat_model
from tools.objective_targets import (
    gen_sat_constraints_from_objective_target as _gen_sat_constraints_from_objective_target,
    parse_objective_target,
    parse_optimal_sat_search_strategy,
)
from tools.search_reporting import log, log_search_summary
import solving.solving as solving


# **************************************************************************** #
# This module provides a interface for SAT-based modeling and solving for automated cryptanalysis, including:
# 1. Search with optimal / at-most / exactly / at-least strategies.
# 2. Generate standard CNF-format models.
# 3. Call the SAT solver (MiniSat, Glucose, etc.) to solve the model.
# **************************************************************************** #


def modeling_solving_sat(objective_target, constraints, objective_function, config_model, config_solver):
    strategy, value = parse_objective_target(objective_target)

    if strategy == "OPTIMAL":
        solutions = modeling_solving_optimal(constraints, objective_function, config_model, config_solver)
    elif strategy == "AT MOST":
        solutions = modeling_solving_at_most(constraints, objective_function, config_model, config_solver, value)
    elif strategy == "EXACTLY":
        solutions = modeling_solving_exactly(constraints, objective_function, config_model, config_solver, value)
    elif strategy == "AT LEAST":
        solutions = modeling_solving_at_least(constraints, objective_function, config_model, config_solver, value)
    elif strategy == "EXISTENCE":
        solutions = modeling_solving(constraints, objective_function, config_model, config_solver)
    else:
        raise ValueError(f"Invalid objective_target: {objective_target}")

    log_search_summary(
        "Modeling and Solving SAT Information",
        solutions,
        config_model,
        config_solver,
        hidden_keys={"positions", "decimal_objective_function"},
    )
    return solutions


# ------------------------- Optimal Search Strategy --------------------------
def modeling_solving_optimal(constraints, objective_function, config_model, config_solver): # Find the optimal SAT solution.
    decimal_objective_function = config_model.get("decimal_objective_function", False)
    if not decimal_objective_function:
        return modeling_solving_optimal_intobj(constraints, objective_function, config_model, config_solver)
    return modeling_solving_optimal_decimalobj(constraints, objective_function, config_model, config_solver)


def modeling_solving_optimal_intobj(constraints, objective_function, config_model, config_solver):
    log("[INFO] Search for the optimal solutions.", config_model, config_solver)

    optimal_search_strategy_sat = config_model.get("optimal_search_strategy_sat", "INCREASING FROM AT MOST 0")
    search_plan = parse_optimal_sat_search_strategy(optimal_search_strategy_sat)
    obj_val = search_plan.start_value
    step = search_plan.step
    end_obj_value = search_plan.end_value
    found_feasible = search_plan.found_feasible
    solutions = None

    while obj_val != end_obj_value:
        log(f"[INFO] Current SAT objective value: {obj_val}", config_model, config_solver)
        if search_plan.constraint_strategy == "AT MOST":
            obj_constraints = gen_sat_constraints_from_objective_target(objective_function, config_model, "SUM_AT_MOST", obj_val, obj_val_decimal=None)
        elif search_plan.constraint_strategy == "EXACTLY":
            obj_constraints = gen_sat_constraints_from_objective_target(objective_function, config_model, "SUM_EXACTLY", obj_val, obj_val_decimal=None)
        current_solutions = modeling_solving(constraints+obj_constraints, objective_function, config_model, config_solver)
        if isinstance(current_solutions, list) and len(current_solutions) > 0:
            for sol in current_solutions:
                sol["integer_obj_fun_value"] = obj_val
        if search_plan.mode == "INCREASING" and current_solutions:
            return current_solutions
        elif search_plan.mode == "DECREASING" and not current_solutions:
            if solutions is None:
                log(
                    f"[INFO] No feasible solution found. Please set the strategy {optimal_search_strategy_sat} with an appropriate starting value.",
                    config_model,
                    config_solver,
                )
                return []
            return solutions
        elif search_plan.mode == "ADAPTIVE":
            if current_solutions and found_feasible is None:
                found_feasible = True
                step = -1
                end_obj_value = -1
            elif (not current_solutions) and found_feasible is True:
                return solutions
            elif (not current_solutions) and found_feasible is None:
                found_feasible = False
            elif current_solutions and found_feasible is False:
                return current_solutions
        obj_val += step
        solutions = current_solutions
    return solutions


def modeling_solving_optimal_decimalobj(constraints, objective_function, config_model, config_solver):
    log("[INFO] Search for the optimal solutions with decimal objective function value.", config_model, config_solver)

    # Step 1: Find the optimal solution with integer objective function value
    solutions = modeling_solving_optimal_intobj(constraints, objective_function, config_model, config_solver)

    # Step 2: Refine search for decimal weights
    if solutions is None or len(solutions) == 0:
        return []
    optimal_search_strategy_sat = config_model.get("optimal_search_strategy_sat", "INCREASING FROM AT MOST 0")
    max_obj_val = solutions[0]["obj_fun_value"] # The current objective function value is the upper bound
    int_obj_val = solutions[0]["integer_obj_fun_value"] # Start searching from the minimal integer objective function value
    log(
        f"[INFO] True objective function value = {max_obj_val} with integer value = {int_obj_val}",
        config_model,
        config_solver,
    )

    if max_obj_val == int_obj_val:
        return solutions

    Sbox = config_model.get("decimal_objective_function", {}).get("Sbox")
    table = config_model.get("decimal_objective_function", {}).get("table")
    if not Sbox or not table:
        raise ValueError("Missing Sbox or table information for decimal objective function search.")
    obj_decimal_list = model_objective.generate_obj_decimal_coms(Sbox, table, int_obj_val, max_obj_val)
    for (true_obj, obj_integer, obj_decimal) in obj_decimal_list:
        if true_obj >= max_obj_val:
            continue
        log(
            f"[INFO] Trying decimal combination with true_obj = {true_obj}, int_obj = {obj_integer}, obj_decimal = {obj_decimal}",
            config_model,
            config_solver,
        )
        if "AT MOST" in optimal_search_strategy_sat:
            obj_constraints = gen_sat_constraints_from_objective_target(objective_function, config_model, "SUM_AT_MOST", obj_integer, obj_val_decimal=obj_decimal)
        elif "EXACTLY" in optimal_search_strategy_sat:
            obj_constraints = gen_sat_constraints_from_objective_target(objective_function, config_model, "SUM_EXACTLY", obj_integer, obj_val_decimal=obj_decimal)
        decimal_solutions = modeling_solving(constraints+obj_constraints, objective_function, config_model, config_solver)
        if isinstance(decimal_solutions, list) and len(decimal_solutions) > 0:
            for sol in decimal_solutions:
                max_obj_val = min(max_obj_val, sol["obj_fun_value"])
                sol["integer_obj_fun_value"] = int_obj_val
            solutions = decimal_solutions
            break
    return solutions


# ------------------------- AT MOST Search Strategy --------------------------
def modeling_solving_at_most(constraints, objective_function, config_model, config_solver, at_most_value):
    log(
        f"[INFO] Search for solutions with the objective function value <= {at_most_value}.",
        config_model,
        config_solver,
    )

    # Search for solutions with integer objective function values <= int(at_most_value)
    obj_constraints = gen_sat_constraints_from_objective_target(objective_function, config_model, "SUM_AT_MOST", int(at_most_value), obj_val_decimal=None)
    solutions = modeling_solving(constraints+obj_constraints, objective_function, config_model, config_solver)

    decimal_objective_function = config_model.get("decimal_objective_function", False)
    if decimal_objective_function and isinstance(solutions, list) and len(solutions) > 0: # For ciphers with S-boxes having decimal weights, further filter and search for one solution with true objective value <= max_val
        for sol in solutions:
            try:
                true_obj = sol.get("obj_fun_value")
            except KeyError:
                log("[WARNING] Solution does not contain 'obj_fun_value'. Skipping.", config_model, config_solver)
            if true_obj <= at_most_value:
                return [sol]
        # If no solution meets the true objective value <= atmost_value, further search
        Sbox = config_model.get("decimal_objective_function", {}).get("Sbox")
        table = config_model.get("decimal_objective_function", {}).get("table")
        if not Sbox or not table:
            raise ValueError("Missing Sbox or table information for decimal objective function search.")
        int_obj_val = int(at_most_value)
        while solutions:
            obj_decimal_list = model_objective.generate_obj_decimal_coms(Sbox, table, int_obj_val, at_most_value)
            for (true_obj, obj_integer, obj_decimal) in reversed(obj_decimal_list):
                if obj_integer > int_obj_val:
                    continue
                log(
                    f"[INFO] Trying decimal combination with true_obj = {true_obj}, int_obj = {obj_integer}, obj_decimal = {obj_decimal}",
                    config_model,
                    config_solver,
                )
                obj_constraints = gen_sat_constraints_from_objective_target(objective_function, config_model, "SUM_AT_MOST", int_obj_val, obj_val_decimal=obj_decimal)
                decimal_solutions = modeling_solving(constraints+obj_constraints, objective_function, config_model, config_solver)
                if isinstance(decimal_solutions, list) and len(decimal_solutions) > 0: # Support searching only a subset of solutions in the multiple-solution setting. TO DO.
                    return decimal_solutions
            int_obj_val -= 1
            obj_constraints = gen_sat_constraints_from_objective_target(objective_function, config_model, "SUM_AT_MOST", int_obj_val, obj_val_decimal=None)
            solutions = modeling_solving(constraints+obj_constraints, objective_function, config_model, config_solver)
    return solutions


# ------------------------- EXACTLY Search Strategy --------------------------
def modeling_solving_exactly(constraints, objective_function, config_model, config_solver, exactly_value):
    log(
        f"[INFO] Search for solutions with the objective function value = {exactly_value}",
        config_model,
        config_solver,
    )

    decimal_objective_function = config_model.get("decimal_objective_function", False)
    if not decimal_objective_function:
        obj_constraints = gen_sat_constraints_from_objective_target(objective_function, config_model, "SUM_EXACTLY", int(exactly_value), obj_val_decimal=None)
        return modeling_solving(constraints+obj_constraints, objective_function, config_model, config_solver)

    EPS = 0.001  # Tolerance for floating-point comparison
    Sbox = config_model.get("decimal_objective_function", {}).get("Sbox")
    table = config_model.get("decimal_objective_function", {}).get("table")
    if not Sbox or not table:
        raise ValueError("Missing Sbox or table information for decimal objective function search.")
    obj_decimal_list = model_objective.generate_obj_decimal_coms(Sbox, table, -1, exactly_value)
    for (true_obj, obj_integer, obj_decimal) in reversed(obj_decimal_list):
        if abs(true_obj - exactly_value) < EPS: # Allow a small tolerance for floating-point comparison
            log(
                f"[INFO] Trying decimal combination with true_obj = {true_obj}, int_obj = {obj_integer}, obj_decimal = {obj_decimal}",
                config_model,
                config_solver,
            )
            obj_constraints = gen_sat_constraints_from_objective_target(objective_function, config_model, "SUM_EXACTLY", obj_integer, obj_val_decimal=obj_decimal)
            solutions = modeling_solving(constraints+obj_constraints, objective_function, config_model, config_solver)
            if isinstance(solutions, list) and len(solutions) > 0:
                return solutions
    return []


# ------------------------- AT LEAST Search Strategy -------------------------
def modeling_solving_at_least(constraints, objective_function, config_model, config_solver, at_least_value):
    log(
        f"[INFO] Search for solutions with objective function value >= {at_least_value}",
        config_model,
        config_solver,
    )

    # Search for solutions with integer objective function values >= int(at_least_value)
    obj_constraints = gen_sat_constraints_from_objective_target(objective_function, config_model, "SUM_AT_LEAST", int(at_least_value), obj_val_decimal=None)
    solutions = modeling_solving(constraints+obj_constraints, objective_function, config_model, config_solver)

    decimal_objective_function = config_model.get("decimal_objective_function", False)
    if decimal_objective_function:
        if solutions:
            for sol in solutions:
                true_obj = sol.get("obj_fun_value")
                if true_obj >= at_least_value:
                    return [sol]
        log("[INFO] No solution found. Need to search further.", config_model, config_solver) # TO DO
        return []
    return solutions


def gen_sat_constraints_from_objective_target(objective_function, config_model, cons_type, obj_val, obj_val_decimal=None):
    return _gen_sat_constraints_from_objective_target(
        objective_function,
        config_model,
        cons_type,
        obj_val,
        obj_val_decimal=obj_val_decimal,
        log=log,
    )

# Core function for modeling and solving SAT.
def modeling_solving(constraints, objective_function, config_model, config_solver):
    log("[INFO] Modeling and solving SAT.", config_model, config_solver)
    model = write_sat_model(constraints=constraints, filename=config_model.get("filename"))
    solutions = solving.solve_sat(config_model.get("filename"), model["variable_map"], config_solver)

    if isinstance(solutions, list) and len(solutions) > 0:
        for sol in solutions:
            round_values = model_objective.cal_round_obj_fun_values_from_solution(objective_function, sol)
            sol["rounds_obj_fun_values"] = round_values
            sol["obj_fun_value"] = sum(round_values)
    return solutions
