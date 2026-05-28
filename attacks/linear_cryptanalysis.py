from math import log2

from attacks import common
from attacks.attack_trace import LinearTrail
import tools.model_constraints as model_constraints
import tools.model_objective as model_objective
import tools.milp_search as milp_search
import tools.sat_search as sat_search
from tools.paths import get_files_dir
from tools.search_reporting import log

FILES_DIR = get_files_dir()


# **************************************************************************** #
# This module is the interface for linear attacks, including:
# 1. search linear trails
# **************************************************************************** #


# ---------------------- Model and Solver Configuration ----------------------
def parse_and_set_configs(cipher, goal, objective_target, config_model, config_solver): # Parse input parameters and apply default values for model and solver configurations.
    return common.parse_and_set_configs(
        cipher, goal, objective_target, config_model, config_solver, many_solution_goal="LINEARHULL_CORR"
    )


# -------------------- Predefined Additional Constraints --------------------
def expand_var_ids(var, bitwise=False): # Expand variable IDs by bits if necessary.
    return common.expand_var_ids(var, bitwise=bitwise)

def gen_input_non_zero_constraints(cipher, goal, config_model): # Generate input non-zero constraints for the cipher based on the goal and model type.
    return common.gen_input_non_zero_constraints(cipher, goal, config_model, truncated_marker="TRUNCATEDLINEAR")

def gen_fixed_input_output_constraints(in_out, fix_mask, cipher, config_model):
    return common.gen_fixed_input_output_constraints(
        in_out, fix_mask, cipher, config_model, value_name="fix_mask"
    )


# ------------------------ Linear Trail Search -------------------------
def search_linear_trail(cipher, goal="LINEARPATH_CORR", constraints=["INPUT_NOT_ZERO"], objective_target="OPTIMAL", show_mode=0, config_model=None, config_solver=None):
    """
    Perform linear attacks on a given cipher using the specified model_type.

    Parameters:
        cipher (Cipher): The cipher object to analyze.
        goal (str): The specific cryptanalysis goal: GOAL or GOAL_OPERATOR_NUMBER
            - LINEAR_SBOXCOUNT
            - LINEARPATH_CORR
            - LINEARHULL_CORR
            - TRUNCATEDLINEAR_SBOXCOUNT
        constraints (list of string): User-specified constraints to be added to the model.
            - ['INPUT_NOT_ZERO']: Automatically add input non-zero constraints as required by the goal.
            - Specific variables constraints, e.g., ['v_1_0_0 = 1', 'v_2_1_0 = 0'] for MILP, ['v_1_0_0', '-v_2_1_0'] for SAT.
            - Any other user-defined constraints.
        objective_target (str): The target for the objective function, which can be:
            - 'OPTIMAL': Find the optimal solution.
            - 'AT MOST X': Find a solution with an objective value at most X.
            - 'EXACTLY X': Find a solution with an objective value exactly X.
            - 'AT LEAST X': Find a solution with an objective value at least X.
            - 'EXISTENCE': Find any feasible solution.
        show_mode (int): The level of solution/result visualization: 0, 1, 2.
        config_model (dict): Optional advanced arguments for modeling, see attacks.parse_and_set_configs() for details.
        config_solver (dict): Optional advanced arguments for solving, see attacks.parse_and_set_configs() for details.

    Returns: A list of linear trail objects.
    """

    assert any(goal.startswith(prefix) for prefix in ["LINEAR_SBOXCOUNT", "LINEARPATH_CORR", "LINEARHULL_CORR", "TRUNCATEDLINEAR_SBOXCOUNT"]), f"Invalid goal: {goal}. Expected one of ['LINEAR_SBOXCOUNT', 'LINEARPATH_CORR', 'LINEARHULL_CORR', 'TRUNCATEDLINEAR_SBOXCOUNT']"
    assert isinstance(constraints, list), f"Invalid constraints: {constraints}. Expected a list of strings."
    assert any(objective_target.startswith(prefix) for prefix in ['OPTIMAL', 'AT MOST', 'EXACTLY', 'AT LEAST', 'EXISTENCE']), f"Invalid objective_target: {objective_target}. Expected one of ['OPTIMAL', 'AT MOST X', 'EXACTLY X', 'AT LEAST X']"
    assert show_mode in [0, 1, 2, 3], f"Invalid show_mode: {show_mode}. Expected one of [0, 1, 2]"
    assert isinstance(config_model, dict) or config_model is None, f"Invalid config_model: {config_model}. Expected a dictionary or None."
    assert isinstance(config_solver, dict) or config_solver is None, f"Invalid config_solver: {config_solver}. Expected a dictionary or None."

    # Generate a new cipher instance with added copy layer after each operator.
    cipher.add_copy_operators()

    # Step 1. Parse and set model and solver configurations.
    config_model, config_solver = parse_and_set_configs(cipher, goal, objective_target, config_model, config_solver)
    model_type = config_model.get("model_type", "milp")

    # Step 2. Generate round constraints and objective function for the cipher.
    round_constraints, obj_fun = model_constraints.gen_round_model_constraint_obj_fun(cipher, goal, model_type, config_model)

    # Step 3. Process additional constraints.
    model_cons = []
    for cons in constraints:
        if cons == "INPUT_NOT_ZERO":  # Deal with specific additional constraints.
            model_cons.extend(gen_input_non_zero_constraints(cipher, goal, config_model))
        else:
            model_cons.append(cons)
    model_cons.extend(round_constraints)

    # For the goal of searching for linear hulls, fix the input and output masks
    if goal == "LINEARHULL_CORR":
        input_mask = config_model.get("input_mask", None)
        output_mask = config_model.get("output_mask", None)
        if input_mask == None and output_mask == None:
            raise ValueError("For goal='LINEARHULL_CORR', either input_mask or output_mask must be specified in config_model.")
        if input_mask is not None:
            model_cons.extend(gen_fixed_input_output_constraints("input", input_mask, cipher, config_model))
        if output_mask is not None:
            model_cons.extend(gen_fixed_input_output_constraints("output", output_mask, cipher, config_model))


    # Step 4: Modeling and Solving.
    if model_type == "milp":
        solutions = milp_search.modeling_solving_milp(objective_target, model_cons, obj_fun, config_model, config_solver)

    elif model_type == "sat":
        if goal in ["LINEARPATH_CORR", "LINEARHULL_CORR"] and model_objective.has_Sbox_with_decimal_weights(cipher, goal):
            config_model["decimal_objective_function"] = {}
            Sbox = model_objective.detect_Sbox(cipher)
            config_model["decimal_objective_function"]["Sbox"] = Sbox
            config_model["decimal_objective_function"]["table"] = Sbox.computeLAT()

        solutions = sat_search.modeling_solving_sat(objective_target, model_cons, obj_fun, config_model, config_solver)

    else:
        raise ValueError(f"Invalid model_type: {model_type}. Expected one of ['milp', 'sat'].")

    # Step 5: Extract and Visualize Trails from Solutions.
    if isinstance(solutions, list):
        return extract_and_format_linear_trails(cipher, goal, config_model, config_solver, show_mode, solutions)

    raise ValueError("[WARNING] No valid solutions found.")


# -------------------- Trail Extraction and Visualization --------------------
def extract_and_format_linear_trails(cipher, goal, config_model, config_solver, show_mode, solutions):
    trails = []
    trail_structs = []
    pr = 0
    for i, sol in enumerate(solutions):
        trail_struct = extract_trail_structures(cipher, goal, sol)
        if trail_struct in trail_structs:
            continue
        trail_structs.append(trail_struct)
        data = {"cipher": f"{cipher.functions['PERMUTATION'].nbr_rounds}_round_{cipher.name}",
                "functions": config_model["functions"],
                "rounds": config_model["rounds"],
                "config_model": config_model,
                "config_solver": config_solver,
                "trail_struct": trail_struct,
                "linear_weight": sol.get("obj_fun_value"),
                "rounds_linear_weight": sol.get("rounds_obj_fun_values")}
        trail = LinearTrail(data, solution_trace=sol)
        if i > 0:
            log(f"[INFO] Saving the {i+1}-th Trail.", config_model, config_solver)
            trail.json_filename = trail.json_filename.replace(".json", f"_{i}.json") if trail.json_filename else str(FILES_DIR / f"{trail.data['cipher']}_trail_{i}.json")
            trail.txt_filename = trail.txt_filename.replace(".txt", f"_{i}.txt") if trail.txt_filename else str(FILES_DIR / f"{trail.data['cipher']}_trail_{i}.txt")
        trail.save_json()
        trail.save_txt(show_mode=show_mode, emit_print=config_model.get("verbose", True))
        trails.append(trail)
        pr += 2 ** ( - trail.data['linear_weight'] ) if trail.data['linear_weight'] is not None else 0
    if solutions and goal == "LINEARHULL_CORR":
        log(f"[INFO] Total correlation of all found trails: 2^{log2(pr) if pr > 0 else 'undefined'}", config_model, config_solver)
    return trails

def extract_trail_structures(cipher, goal, solution):
    """
    Extract a structured linear trail (trail_struct) from a solver assignment.

    Returned structure (example):
    """
    return common.extract_trail_structures(cipher, goal, solution, truncated_marker="TRUNCATEDLINEAR")
