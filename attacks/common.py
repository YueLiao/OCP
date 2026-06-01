"""Shared helpers for differential and linear attack frontends."""

from dataclasses import dataclass
from math import log2

from tools.model_configuration import fill_functions_rounds_layers_positions
from tools.model_generation_state import IDENTITY_ELISION_ALIASES_KEY, rewrite_token_with_alias
from tools.objective_targets import parse_objective_target
from tools.predefined_constraints import gen_predefined_constraints
from tools.paths import get_files_dir
from tools.search_reporting import log


@dataclass(frozen=True)
class AttackSearchConfig:
    """Typed wrapper for normalized attack model/solver dictionaries."""

    model: dict
    solver: dict

    @property
    def model_type(self):
        return self.model["model_type"]

    @property
    def filename(self):
        return self.model["filename"]

    def as_dicts(self):
        """Return legacy dictionaries expected by existing search helpers."""

        return self.model, self.solver


def normalize_model_type(model_type):
    """Normalize and validate supported model backend types."""

    normalized = str(model_type).lower()
    if normalized not in ("milp", "sat"):
        raise ValueError(f"Invalid model_type: {model_type}. Expected one of ['milp', 'sat'].")
    return normalized


def default_model_filename(cipher, goal, objective_target, model_type):
    """Return the default runtime model filename for a configured attack."""

    suffix = "milp_model.lp" if model_type == "milp" else "sat_model.cnf"
    return str(
        get_files_dir()
        / f"{cipher.nbr_rounds}round_{cipher.name}_{goal}_{objective_target}_{suffix}"
    )


def normalize_solution_number(value):
    """Validate solver solution count settings used by attack frontends."""

    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"Invalid solution_number: {value}. Expected a positive integer.")
    return value


def validate_attack_search_request(
    goal,
    allowed_goal_prefixes,
    constraints,
    objective_target,
    show_mode,
    config_model,
    config_solver,
):
    """Validate public attack-search arguments at the API boundary."""

    if not any(goal.startswith(prefix) for prefix in allowed_goal_prefixes):
        raise ValueError(f"Invalid goal: {goal}. Expected one of {list(allowed_goal_prefixes)}.")
    if not isinstance(constraints, list):
        raise ValueError(f"Invalid constraints: {constraints}. Expected a list of strings.")
    if any(not isinstance(constraint, str) for constraint in constraints):
        raise ValueError(f"Invalid constraints: {constraints}. Expected a list of strings.")
    try:
        parse_objective_target(objective_target)
    except ValueError as exc:
        raise ValueError(
            f"Invalid objective_target: {objective_target}. Expected one of "
            "['OPTIMAL', 'AT MOST X', 'EXACTLY X', 'AT LEAST X', 'EXISTENCE']."
        ) from exc
    if show_mode not in [0, 1, 2, 3]:
        raise ValueError(f"Invalid show_mode: {show_mode}. Expected one of [0, 1, 2, 3].")
    if not (isinstance(config_model, dict) or config_model is None):
        raise ValueError(f"Invalid config_model: {config_model}. Expected a dictionary or None.")
    if not (isinstance(config_solver, dict) or config_solver is None):
        raise ValueError(f"Invalid config_solver: {config_solver}. Expected a dictionary or None.")


def build_attack_search_config(cipher, goal, objective_target, config_model, config_solver, many_solution_goal=None):
    """Apply common model and solver defaults for attack search."""

    config_model = dict(config_model or {})
    config_solver = dict(config_solver or {})
    config_model["model_type"] = normalize_model_type(config_model.get("model_type", "milp"))

    functions, rounds, layers, positions = fill_functions_rounds_layers_positions(cipher)
    config_model.setdefault("functions", functions)
    config_model.setdefault("rounds", rounds)
    config_model.setdefault("layers", layers)
    config_model.setdefault("positions", positions)
    config_solver.setdefault("solver", "DEFAULT")

    config_model.setdefault(
        "filename",
        default_model_filename(cipher, goal, objective_target, config_model["model_type"]),
    )

    if many_solution_goal and goal == many_solution_goal:
        config_solver.setdefault("solution_number", 1000000)
    if "solution_number" in config_solver:
        config_solver["solution_number"] = normalize_solution_number(config_solver["solution_number"])

    return AttackSearchConfig(model=config_model, solver=config_solver)


def parse_and_set_configs(cipher, goal, objective_target, config_model, config_solver, many_solution_goal=None):
    """Apply common model and solver defaults and return legacy dictionaries."""

    return build_attack_search_config(
        cipher,
        goal,
        objective_target,
        config_model,
        config_solver,
        many_solution_goal=many_solution_goal,
    ).as_dicts()


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
    constraints = gen_predefined_constraints(
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


def gen_additional_constraints(cipher, goal, constraints, config_model, truncated_marker):
    """Expand symbolic attack constraints into concrete model constraints."""

    model_constraints = []
    for constraint in constraints:
        if constraint == "INPUT_NOT_ZERO":
            model_constraints.extend(
                gen_input_non_zero_constraints(cipher, goal, config_model, truncated_marker=truncated_marker)
            )
        else:
            model_constraints.append(constraint)
    return model_constraints


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
        try:
            bits = bin(int(text, 16))[2:].zfill(bit_count)
        except ValueError as exc:
            raise ValueError(
                f"[WARNING] Invalid {value_name} format: {fixed_value}. "
                "Expected binary (0b...) or hexadecimal (0x...) string."
            ) from exc
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


def gen_required_fixed_boundary_constraints(
    goal,
    required_goal,
    cipher,
    config_model,
    input_value,
    output_value,
    input_label,
    output_label,
    value_name,
):
    """Generate fixed input/output constraints required by hull/probability goals."""

    if goal != required_goal:
        return []
    if input_value is None and output_value is None:
        raise ValueError(
            f"For goal='{required_goal}', either {input_label} or {output_label} "
            "must be specified in config_model."
        )

    constraints = []
    if input_value is not None:
        constraints.extend(
            gen_fixed_input_output_constraints("input", input_value, cipher, config_model, value_name)
        )
    if output_value is not None:
        constraints.extend(
            gen_fixed_input_output_constraints("output", output_value, cipher, config_model, value_name)
        )
    return constraints


def solution_bit(solution, var_id, aliases=None):
    """Map a solver value to '0', '1', or '-'."""

    value = solution.get(var_id, None)
    if value is None and aliases:
        value = solution.get(rewrite_token_with_alias(var_id, aliases), None)
    if value is None:
        return "-"
    try:
        return "1" if int(round(value)) == 1 else "0"
    except (TypeError, ValueError, OverflowError):
        return "-"


def extract_trail_structures(cipher, goal, solution, truncated_marker, config_model=None):
    """Extract a structured trail from a solver assignment."""

    bitwise = truncated_marker not in goal
    aliases = (config_model or {}).get(IDENTITY_ELISION_ALIASES_KEY) or {}

    def node(var):
        ids = expand_var_ids(var, bitwise=bitwise)
        bits = "".join(solution_bit(solution, var_id, aliases=aliases) for var_id in ids)
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


def extract_and_format_trails(
    cipher,
    goal,
    config_model,
    config_solver,
    show_mode,
    solutions,
    trail_class,
    extract_trail_structures_func,
    weight_key,
    rounds_weight_key,
    aggregate_goal,
    aggregate_label,
    include_aggregate_count=True,
):
    """Create trail objects, save artifacts, and report aggregate probability/correlation."""

    trails = []
    trail_structs = []
    aggregate_value = 0
    for i, solution in enumerate(solutions):
        trail_struct = extract_trail_structures_func(cipher, goal, solution, config_model)
        if trail_struct in trail_structs:
            continue
        trail_structs.append(trail_struct)
        data = {
            "cipher": f"{cipher.functions['PERMUTATION'].nbr_rounds}_round_{cipher.name}",
            "functions": config_model["functions"],
            "rounds": config_model["rounds"],
            "config_model": config_model,
            "config_solver": config_solver,
            "trail_struct": trail_struct,
            weight_key: solution.get("obj_fun_value"),
            rounds_weight_key: solution.get("rounds_obj_fun_values"),
        }
        trail = trail_class(data, solution_trace=solution)
        if i > 0:
            log(f"[INFO] Saving the {i+1}-th Trail.", config_model, config_solver)
            trail.json_filename = (
                trail.json_filename.replace(".json", f"_{i}.json")
                if trail.json_filename
                else str(get_files_dir() / f"{trail.data['cipher']}_trail_{i}.json")
            )
            trail.txt_filename = (
                trail.txt_filename.replace(".txt", f"_{i}.txt")
                if trail.txt_filename
                else str(get_files_dir() / f"{trail.data['cipher']}_trail_{i}.txt")
            )
        trail.save_json()
        trail.save_txt(show_mode=show_mode, emit_print=config_model.get("verbose", True))
        trails.append(trail)
        aggregate_value += 2 ** (-trail.data[weight_key]) if trail.data[weight_key] is not None else 0
    if solutions and goal == aggregate_goal:
        count_text = f"all {len(trails)} found trails" if include_aggregate_count else "all found trails"
        log(
            f"[INFO] Total {aggregate_label} of {count_text}: "
            f"2^{log2(aggregate_value) if aggregate_value > 0 else 'undefined'}",
            config_model,
            config_solver,
        )
    return trails
