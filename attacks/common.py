"""Shared helpers for differential and linear attack frontends."""

import tools.model_constraints as model_constraints
from tools.paths import get_files_dir


def parse_and_set_configs(cipher, goal, objective_target, config_model, config_solver, many_solution_goal=None):
    """Apply common model and solver defaults for attack search."""

    config_model = config_model or {}
    config_solver = config_solver or {}
    config_model["model_type"] = config_model.get("model_type", "milp").lower()

    functions, rounds, layers, positions = model_constraints.fill_functions_rounds_layers_positions(cipher)
    config_model.setdefault("functions", functions)
    config_model.setdefault("rounds", rounds)
    config_model.setdefault("layers", layers)
    config_model.setdefault("positions", positions)
    config_solver.setdefault("solver", "DEFAULT")

    model_type = config_model["model_type"]
    if model_type == "milp":
        suffix = "milp_model.lp"
    elif model_type == "sat":
        suffix = "sat_model.cnf"
    else:
        raise ValueError(f"Invalid model_type: {model_type}. Expected one of ['milp', 'sat'].")

    config_model["filename"] = str(
        get_files_dir() / f"{cipher.nbr_rounds}round_{cipher.name}_{goal}_{objective_target}_{suffix}"
    )

    if many_solution_goal and goal == many_solution_goal:
        config_solver.setdefault("solution_number", 1000000)

    return config_model, config_solver


def expand_var_ids(var, bitwise=False):
    """Expand a variable into model variable IDs."""

    if bitwise and var.bitsize > 1:
        return [f"{var.ID}_{i}" for i in range(var.bitsize)]
    return [var.ID]


def gen_input_non_zero_constraints(cipher, goal, config_model, truncated_marker):
    """Generate the standard nonzero input constraint."""

    cons_vars = [var for cons in cipher.inputs_constraints for var in cons.input_vars]
    model_type = config_model.get("model_type", "milp").lower()
    encoding = config_model.get("atleast_encoding_sat", "SEQUENTIAL") if model_type == "sat" else None
    bitwise = truncated_marker not in goal
    constraints = model_constraints.gen_predefined_constraints(
        model_type=model_type,
        cons_type="SUM_AT_LEAST",
        cons_vars=cons_vars,
        cons_value=1,
        bitwise=bitwise,
        encoding=encoding,
    )
    if model_type == "milp":
        binary_vars = [var_id for var in cons_vars for var_id in expand_var_ids(var, bitwise=bitwise)]
        if binary_vars:
            constraints.append("Binary\n" + " ".join(binary_vars))
    return constraints


def _cipher_boundary_vars(in_out, cipher):
    cons_vars = []
    if in_out == "input":
        if not hasattr(cipher, "inputs") or not isinstance(cipher.inputs, dict):
            raise ValueError("[WARNING] Cipher 'inputs' attribute invalid.")
        for input_name in cipher.inputs:
            cons_vars += cipher.inputs[input_name]
    elif in_out == "output":
        if not hasattr(cipher, "outputs") or not isinstance(cipher.outputs, dict):
            raise ValueError("[WARNING] Cipher 'outputs' attribute invalid.")
        for output_name in cipher.outputs:
            cons_vars += cipher.outputs[output_name]
    else:
        raise ValueError(f"[WARNING] Invalid in_out: {in_out}. Expected 'input' or 'output'.")

    if not cons_vars:
        raise ValueError(f"[WARNING] Cipher has no {in_out} variables.")
    return cons_vars


def normalize_fixed_value_bits(fixed_value, bit_count, value_name):
    """Normalize a binary or hexadecimal fixed mask/difference string to bits."""

    text = fixed_value.strip().lower()
    if text.startswith("0b"):
        bits = text[2:].zfill(bit_count)
    elif text.startswith("0x"):
        bits = bin(int(text, 16))[2:].zfill(bit_count)
    else:
        raise ValueError(
            f"[WARNING] Invalid {value_name} format: {fixed_value}. "
            "Expected binary (0b...) or hexadecimal (0x...) string."
        )

    if len(bits) > bit_count:
        raise ValueError(
            f"[WARNING] {value_name} has {len(bits)} bits but the {bit_count}-bit boundary was expected."
        )
    return bits


def gen_fixed_input_output_constraints(in_out, fixed_value, cipher, config_model, value_name):
    """Generate constraints that fix input/output differences or masks."""

    cons_vars = _cipher_boundary_vars(in_out, cipher)
    bit_count = sum(var.bitsize for var in cons_vars)
    bits = normalize_fixed_value_bits(fixed_value, bit_count, value_name)
    model_type = config_model.get("model_type", "milp").lower()

    constraints = []
    offset = 0
    for var in cons_vars:
        if var.bitsize == 1:
            bit = bits[offset]
            var_id = var.ID
            offset += 1
            if model_type == "sat":
                constraints.append(var_id if bit == "1" else f"-{var_id}")
            elif model_type == "milp":
                constraints.append(f"{var_id} = {bit}")
                constraints.append("Binary\n" + var_id)
            else:
                raise ValueError(f"Invalid model_type: {model_type}. Expected one of ['milp', 'sat'].")
            continue

        for bit_index in range(var.bitsize):
            bit = bits[offset + bit_index]
            var_id = f"{var.ID}_{bit_index}"
            if model_type == "sat":
                constraints.append(var_id if bit == "1" else f"-{var_id}")
            elif model_type == "milp":
                constraints.append(f"{var_id} = {bit}")
                constraints.append("Binary\n" + var_id)
            else:
                raise ValueError(f"Invalid model_type: {model_type}. Expected one of ['milp', 'sat'].")
        offset += var.bitsize
    return constraints


def solution_bit(solution, var_id):
    """Map a solver value to '0', '1', or '-'."""

    value = solution.get(var_id, None)
    if value is None:
        return "-"
    try:
        return "1" if int(round(value)) == 1 else "0"
    except (TypeError, ValueError, OverflowError):
        return "-"


def extract_trail_structures(cipher, goal, solution, truncated_marker):
    """Extract a structured trail from a solver assignment."""

    bitwise = truncated_marker not in goal

    def node(var):
        ids = expand_var_ids(var, bitwise=bitwise)
        bits = "".join(solution_bit(solution, var_id) for var_id in ids)
        return {
            "var_ID": getattr(var, "ID", str(var)),
            "variables": ids,
            "bin_values": bits,
        }

    trail_struct = {
        "bitwise": bitwise,
        "inputs": {},
        "outputs": {},
        "functions": {},
    }

    if hasattr(cipher, "inputs") and isinstance(cipher.inputs, dict):
        for name, var_list in cipher.inputs.items():
            trail_struct["inputs"][name] = [node(v) for v in var_list]
    if hasattr(cipher, "outputs") and isinstance(cipher.outputs, dict):
        for name, var_list in cipher.outputs.items():
            trail_struct["outputs"][name] = [node(v) for v in var_list]

    for fun in cipher.functions:
        cipher_function = cipher.functions[fun]
        fun_store = {
            "rounds": list(range(1, cipher_function.nbr_rounds + 1)),
            "nbr_words": cipher_function.nbr_words if hasattr(cipher_function, "nbr_words") else None,
            "nbr_temp_words": cipher_function.nbr_temp_words if hasattr(cipher_function, "nbr_temp_words") else None,
        }
        for round_index in range(1, cipher_function.nbr_rounds + 1):
            round_store = {}
            for layer_index in range(cipher_function.nbr_layers + 1):
                round_store[layer_index] = [node(v) for v in cipher_function.vars[round_index][layer_index]]
            fun_store[round_index] = round_store
        trail_struct["functions"][fun] = fun_store
    return trail_struct
