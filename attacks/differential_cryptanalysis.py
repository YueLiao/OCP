from attacks import common
from attacks.attack_trace import DifferentialTrail
from tools.model_configuration import gen_round_model_constraint_obj_fun
import tools.model_objective as model_objective
import tools.milp_search as milp_search
import tools.sat_search as sat_search


# **************************************************************************** #
# This module is the interface for differential attacks, including:
# 1. search differential trails
# **************************************************************************** #


# ---------------------- Model and Solver Configuration ----------------------
def parse_and_set_configs(cipher, goal, objective_target, config_model, config_solver): # Parse input parameters and apply default values for model and solver configurations.
    return common.parse_and_set_configs(
        cipher, goal, objective_target, config_model, config_solver, many_solution_goal="DIFFERENTIAL_PROB"
    )


# -------------------- Predefined Additional Constraints --------------------
def expand_var_ids(var, bitwise=False): # Expand variable IDs by bits if necessary.
    return common.expand_var_ids(var, bitwise=bitwise)

def gen_input_non_zero_constraints(cipher, goal, config_model): # Generate input non-zero constraints for the cipher based on the goal and model type.
    return common.gen_input_non_zero_constraints(cipher, goal, config_model, truncated_marker="TRUNCATEDDIFF")


def gen_fixed_input_output_constraints(in_out, fix_diff, cipher, config_model):
    return common.gen_fixed_input_output_constraints(
        in_out, fix_diff, cipher, config_model, value_name="fix_diff"
    )


# ------------------------ Differential Trail Search -------------------------
def search_diff_trail(cipher, goal="DIFFERENTIALPATH_PROB", constraints=["INPUT_NOT_ZERO"], objective_target="OPTIMAL", show_mode=0, config_model=None, config_solver=None):
    """
    Perform differential attacks on a given cipher using the specified model_type.

    Parameters:
        cipher (Cipher): The cipher object to analyze.
        goal (str): The specific cryptanalysis goal: GOAL or GOAL_OPERATOR_NUMBER
            - DIFFERENTIAL_SBOXCOUNT
            - DIFFERENTIALPATH_PROB
            - DIFFERENTIAL_PROB
            - TRUNCATEDDIFF_SBOXCOUNT
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

    Returns: A list of differential trail objects.
    """

    common.validate_attack_search_request(
        goal,
        ["DIFFERENTIAL_SBOXCOUNT", "DIFFERENTIALPATH_PROB", "DIFFERENTIAL_PROB", "TRUNCATEDDIFF_SBOXCOUNT"],
        constraints,
        objective_target,
        show_mode,
        config_model,
        config_solver,
    )

    # Step 1. Parse and set model and solver configurations.
    config_model, config_solver = parse_and_set_configs(cipher, goal, objective_target, config_model, config_solver)
    model_type = config_model.get("model_type", "milp")

    # Step 2. Generate round constraints and objective function for the cipher.
    round_constraints, obj_fun = gen_round_model_constraint_obj_fun(cipher, goal, model_type, config_model)

    # Step 3. Process additional constraints.
    model_cons = common.gen_additional_constraints(
        cipher, goal, constraints, config_model, truncated_marker="TRUNCATEDDIFF"
    )
    model_cons.extend(round_constraints)

    # For the goal of searching for differentials, fix the input and output differences
    model_cons.extend(
        common.gen_required_fixed_boundary_constraints(
            goal,
            "DIFFERENTIAL_PROB",
            cipher,
            config_model,
            config_model.get("input_diff"),
            config_model.get("output_diff"),
            "input_diff",
            "output_diff",
            "fix_diff",
        )
    )

    # Step 4: Modeling and Solving.
    if model_type == "milp":
        solutions = milp_search.modeling_solving_milp(objective_target, model_cons, obj_fun, config_model, config_solver)

    elif model_type == "sat":
        if goal in ["DIFFERENTIALPATH_PROB", "DIFFERENTIAL_PROB"] and model_objective.has_Sbox_with_decimal_weights(cipher, goal):
            config_model["decimal_objective_function"] = {}
            Sbox = model_objective.detect_Sbox(cipher)
            config_model["decimal_objective_function"]["Sbox"] = Sbox
            if goal in {'DIFFERENTIALPATH_PROB', 'DIFFERENTIAL_PROB'}:
                config_model["decimal_objective_function"]["table"] = Sbox.computeDDT()

        solutions = sat_search.modeling_solving_sat(objective_target, model_cons, obj_fun, config_model, config_solver)

    else:
        raise ValueError(f"Invalid model_type: {model_type}. Expected one of ['milp', 'sat'].")

    # Step 5: Extract and Visualize Trails from Solutions.
    if isinstance(solutions, list):
        return extract_and_format_diff_trails(cipher, goal, config_model, config_solver, show_mode, solutions)

    raise ValueError("[WARNING] No valid solutions found.")


# -------------------- Trail Extraction and Visualization --------------------
def extract_and_format_diff_trails(cipher, goal, config_model, config_solver, show_mode, solutions):
    return common.extract_and_format_trails(
        cipher,
        goal,
        config_model,
        config_solver,
        show_mode,
        solutions,
        DifferentialTrail,
        extract_trail_structures,
        "diff_weight",
        "rounds_diff_weight",
        "DIFFERENTIAL_PROB",
        "probability",
    )

def extract_trail_structures(cipher, goal, solution, config_model=None):
    """
    Extract a structured differential trail (trail_struct) from a solver assignment.

    Returned structure (example):
    """
    return common.extract_trail_structures(
        cipher,
        goal,
        solution,
        truncated_marker="TRUNCATEDDIFF",
        config_model=config_model,
    )
