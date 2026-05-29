from tools import bit_constraints
from tools import model_templates
from tools import sat_cardinality
from tools import search_constraints
from tools.model_generation_state import (
    IDENTITY_ELISION_ALIASES_KEY,
    IDENTITY_ELISION_PROFILE_KEY,
    MODEL_GENERATION_PROFILE_ENABLED_KEY,
    MODEL_GENERATION_PROFILE_KEY,
    apply_identity_aliases as _apply_identity_aliases,
    configure_identity_elision as _configure_identity_elision,
    generate_model_with_profile as _generate_model_with_profile,
    identity_elision_prefix_key as _identity_elision_prefix_key,
    is_identity_elision_candidate as _is_identity_elision_candidate,
    profile_operator_prefix as _profile_operator_prefix,
    reset_model_generation_profile as _reset_model_generation_profile,
    rewrite_token_with_alias as _rewrite_token_with_alias,
)
CardEnc = sat_cardinality.CardEnc
vpool = sat_cardinality.vpool
pysat_import = sat_cardinality.pysat_import


def _sync_pysat_cardinality_state():
    global CardEnc, pysat_import, vpool

    CardEnc = sat_cardinality.CardEnc
    vpool = sat_cardinality.vpool
    pysat_import = sat_cardinality.pysat_import


def _load_pysat_cardinality_backend():
    backend = sat_cardinality.load_pysat_cardinality_backend()
    _sync_pysat_cardinality_state()
    return backend


def _require_pysat_cardenc():
    card_enc = sat_cardinality.require_pysat_cardenc()
    _sync_pysat_cardinality_state()
    return card_enc


def _pysat_cardinality_error_types():
    return sat_cardinality.pysat_cardinality_error_types()


# **************************************************************************** #
# This module provides the unified interface for generating MILP/SAT model constraints for cryptanalysis, including:
# 1. Cipher Model Configuration
#    - Assign model versions based on attack goals
#    - Generate constraints and objective functions
# 2. Constraint Generation Utilities
#    - Predefined constraints (EXACTLY, AT_LEAST, SUM_AT_MOST, etc.)
#    - SAT sequential encoding for cardinality constraints
# 3. Advanced Search Strategies
#    - Matsui’s branch-and-bound acceleration techniques for MILP and SAT-based differential and linear trail searches
# **************************************************************************** #


# --------------------------- Model Configuration ---------------------------
def fill_functions_rounds_layers_positions(cipher, functions=None, rounds=None, layers=None, positions=None):
    """
    Fill in functions, rounds, layers, and positions to full coverage when the corresponding argument is None; otherwise, keep user-supplied values.

    Parameters:
        cipher (object): The cipher object.
        functions (list[str]): List of functions. If None, use all functions of the cipher. Example: ["PERMUTATION", "KEY_SCHEDULE", "SUBKEYS"].
        rounds (dict): Dictionary specifying rounds. If None, use all. Example: {"PERMUTATION": [1, 2, 3]}.
        layers (dict): Dictionary specifying layers. If None, use all. Example: {"PERMUTATION": {1: [0, 1], 2: [0, 1], 3: [0, 1]}}.
        positions (dict): Dictionary specifying positions. If None, use all. Example: {"PERMUTATION": {1: {0: [0, 1], 1: [0, 1]}, 2: {0: [0, 1], 1: [0, 1]}, 3: {0: [0, 1], 1: [0, 1]}}}.

    Returns:
        tuple: (functions, rounds, layers, positions)
    """
    if functions is None:
        functions = [f for f in cipher.functions]
    if rounds is None:
        rounds = {f: list(range(1, cipher.functions[f].nbr_rounds + 1)) for f in functions}
    if layers is None:
        layers = {f: {r: list(range(cipher.functions[f].nbr_layers+1)) for r in rounds[f]} for f in functions}
    if positions is None:
        positions = {f: {r: {l: list(range(len(cipher.functions[f].constraints[r][l]))) for l in layers[f][r]} for r in rounds[f]} for f in functions}
    return functions, rounds, layers, positions


def configure_model_version(cipher, goal, config_model): # Configure the model version for all operators in the cipher based on the attack goal and config_model.
    functions, rounds, layers, positions = config_model.get("functions"), config_model.get("rounds"), config_model.get("layers"), config_model.get("positions")

    if goal == 'DIFFERENTIAL_SBOXCOUNT':
        set_model_versions(cipher, "XORDIFF", functions, rounds, layers, positions) # Set model_version = "XORDIFF" for all operators
        set_model_versions(cipher, "XORDIFF_A", functions, rounds, layers, positions, operator_name="Sbox") # Set model_version = "XORDIFF_A" for all Sbox operators

    elif goal == 'DIFFERENTIALPATH_PROB' or  goal == "DIFFERENTIAL_PROB":
        set_model_versions(cipher, "XORDIFF", functions, rounds, layers, positions) # Set model_version = "XORDIFF" for all operators
        set_model_versions(cipher, "XORDIFF_PR", functions, rounds, layers, positions, operator_name="Sbox") # Set model_version = "XORDIFF_PR" for all Sbox operators

    elif goal == 'LINEAR_SBOXCOUNT':
        set_model_versions(cipher, "LINEAR", functions, rounds, layers, positions) # Set model_version = "LINEAR" for all operators
        set_model_versions(cipher, "LINEAR_A", functions, rounds, layers, positions, operator_name="Sbox") # Set model_version = "LINEAR_A" for all Sbox operators

    elif goal == 'LINEARPATH_CORR' or goal == "LINEARHULL_CORR":
        set_model_versions(cipher, "LINEAR", functions, rounds, layers, positions) # Set model_version = "LINEAR" for all operators
        set_model_versions(cipher, "LINEAR_PR", functions, rounds, layers, positions, operator_name="Sbox") # Set model_version = "LINEAR_PR" for all Sbox operators

    elif goal == "TRUNCATEDDIFF_SBOXCOUNT":
        set_model_versions(cipher, "TRUNCATEDDIFF", functions, rounds, layers, positions) # Set model_version = "TRUNCATEDDIFF" for all operators
        set_model_versions(cipher, "TRUNCATEDDIFF_A", functions, rounds, layers, positions, operator_name="Sbox") # Set model_version = "TRUNCATEDDIFF_A" for all Sbox operators

    elif goal == "TRUNCATEDLINEAR_SBOXCOUNT":
        set_model_versions(cipher, "TRUNCATEDLINEAR", functions, rounds, layers, positions) # Set model_version = "TRUNCATEDLINEAR" for all operators
        set_model_versions(cipher, "TRUNCATEDLINEAR_A", functions, rounds, layers, positions, operator_name="Sbox") # Set model_version = "TRUNCATEDLINEAR_A" for all Sbox operators

    else:
        raise ValueError(f"Invalid goal: {goal}.")

    if "model_version" in config_model: # Set a specific model version for an operator. Example: config_model['model_version'] = {'model_version': 'XOR_XORDIFF_1', 'operator_name': 'XOR'}.
        version = config_model.get("model_version").get("model_version")
        operator_name = config_model.get("model_version").get("operator_name", None)
        set_model_versions(cipher, version, functions, rounds, layers, positions, operator_name=operator_name)


def set_model_versions(cipher, version, functions, rounds, layers, positions, operator_name=None): # Assigns a specified model_version to constraints (operators) in the cipher based on specified parameters.
    def _assgn_version(cons):
        if operator_name is None: # Assign model_version to all operators in the cipher.
            cons.model_version = cons.__class__.__name__ + "_" + version
        elif operator_name is not None and (operator_name == cons.__class__.__name__ or (operator_name=="Sbox" and cons.__class__.__name__.endswith("Sbox"))): # Assign model_version to operators with a specific name.
            cons.model_version = cons.__class__.__name__ + "_" + version

    # Assign model_version to input/output constraints
    for cons in cipher.inputs_constraints:
        _assgn_version(cons)
    for cons in cipher.outputs_constraints:
        _assgn_version(cons)

    # Assign model_version to function
    for f in functions:
        for r in rounds[f]:
            for l in layers[f][r]:
                for cons in cipher.functions[f].constraints[r][l]: # Only support all constraints in a layer for now.
                    _assgn_version(cons)


def gen_round_model_constraint_obj_fun(cipher, goal, model_type, config_model): # Generate constraints for a given cipher based on user-specified parameters.
    configure_model_version(cipher, goal, config_model)
    _reset_model_generation_profile(config_model)
    _configure_identity_elision(cipher, config_model)
    constraint = []
    obj_fun = [[] for _ in range(cipher.functions["PERMUTATION"].nbr_rounds)]

    # Generate constraints linking input and output
    for cons in cipher.inputs_constraints:
        constraint.extend(_generate_model_with_profile(cons, model_type, config_model))
    for cons in cipher.outputs_constraints:
        constraint.extend(_generate_model_with_profile(cons, model_type, config_model))

    # Generate constraints and objective function for each round/layer/operator
    functions, rounds, layers, positions = config_model.get("functions"), config_model.get("rounds"), config_model.get("layers"), config_model.get("positions")
    for f in functions:
        for r in rounds[f]:
            for l in layers[f][r]:
                for i in positions[f][r][l]:
                    cons = cipher.functions[f].constraints[r][l][i]
                    cons_class_name = cons.__class__.__name__
                    params = (config_model.get("model_params") or {}).get(cons_class_name, {}) # get operator-specific params if available. Options: {cons_class_name: {parame_name: param_value}}. Example: config_model["model_params"] = {"PRESENT_Sbox": {"tool_type": "polyhedron"}}
                    constraint.extend(_generate_model_with_profile(cons, model_type, config_model, **params))
                    if hasattr(cons, 'weight'):
                        obj_fun[r-1].extend(_apply_identity_aliases(cons.weight, config_model.get(IDENTITY_ELISION_ALIASES_KEY) or {}))
    return constraint, obj_fun


# -------------------- Predefined Constraint Generation --------------------
def _expand_constraint_vars(cons_vars, bitwise=True):
    cons_vars_name = []
    for var in cons_vars:
        if isinstance(var, str):
            cons_vars_name.append(var)
        elif bitwise and var.bitsize > 1:
            cons_vars_name.extend(f"{var.ID}_{j}" for j in range(var.bitsize))
        else:
            cons_vars_name.append(var.ID)
    return cons_vars_name


def _readable_cardinality_clauses(cnf, reverse_map):
    return sat_cardinality.readable_cardinality_clauses(cnf, reverse_map)


def _pysat_cardinality_constraints(cons_vars, cons_value, encoding, encoder, encoder_name):
    return sat_cardinality.pysat_cardinality_constraints(
        cons_vars,
        cons_value,
        encoding,
        encoder,
        encoder_name,
        backend_loader=_load_pysat_cardinality_backend,
        error_types_loader=_pysat_cardinality_error_types,
    )


def gen_predefined_constraints(model_type, cons_type, cons_vars, cons_value, bitwise=True, encoding=None):
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
    if cons_type in ["EXACTLY", "SUM_EXACTLY", "AT_LEAST", "SUM_AT_LEAST", "AT_MOST", "SUM_AT_MOST"]:
        cons_vars_name = _expand_constraint_vars(cons_vars, bitwise=bitwise)
        if cons_type == "EXACTLY":
            return gen_constraints_exactly(model_type, cons_vars_name, cons_value)
        elif cons_type == "SUM_EXACTLY":
            return gen_constraints_sum_exactly(model_type, cons_vars_name, cons_value, encoding)
        elif cons_type == "AT_MOST":
            return gen_constraints_at_most(model_type, cons_vars_name, cons_value)
        elif cons_type == "SUM_AT_MOST":
            return gen_constraints_sum_at_most(model_type, cons_vars_name, cons_value, encoding)
        elif cons_type == "AT_LEAST":
            return gen_constraints_at_least(model_type, cons_vars_name, cons_value)
        elif cons_type == "SUM_AT_LEAST":
            return gen_constraints_sum_at_least(model_type, cons_vars_name, cons_value, encoding)
    raise ValueError(f"Unsupported cons_type '{cons_type}'.")

def gen_constraints_exactly(model_type, cons_vars, cons_value):
    if model_type == "milp":
        return [f"{cons_vars[i]} = {cons_value}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 0:
        return [f"-{cons_vars[i]}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 1:
        return [f"{cons_vars[i]}" for i in range(len(cons_vars))]
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for EXACTLY constraint.")

def gen_constraints_sum_exactly(model_type, cons_vars, cons_value, encoding=1):
    if model_type == "milp":
        return [' + '.join(f"{cons_vars[i]}" for i in range(len(cons_vars))) + f" = {cons_value}"]
    elif model_type == "sat" and cons_value == 0:
        return [f"-{cons_vars[i]}" for i in range(len(cons_vars))]
    elif model_type == "sat" and pysat_import:
        if not encoding:
            encoding = 1  # Default to 1 if not specified
        assert encoding in [0,1,2,3,4,5,6,7,8,9], f"[ERROR] Invalid encoding = {encoding}, refer https://pysathq.github.io/docs/html/api/card.html"
        card_enc = _require_pysat_cardenc()
        return _pysat_cardinality_constraints(cons_vars, cons_value, encoding, card_enc.equals, "equals")
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for SUM_EXACTLY constraint.")

def gen_constraints_at_most(model_type, cons_vars, cons_value):
    if model_type == "milp":
        return [f"{cons_vars[i]} <= {cons_value}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 0:
        return [f"-{cons_vars[i]}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 1:
        return []
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for AT_MOST constraint.")

def gen_constraints_sum_at_most(model_type, cons_vars, cons_value, encoding="SEQUENTIAL"):
    if model_type == "milp":
        return [' + '.join(f"{cons_vars[i]}" for i in range(len(cons_vars))) + f" <= {cons_value}"]
    elif model_type == "sat" and (encoding == "SEQUENTIAL" or encoding is None):
        return gen_sequential_encoding_sat(cons_vars, cons_value)
    elif model_type == "sat" and pysat_import:
        if not isinstance(encoding, int):
            encoding = 1  # Default to 1 if the encoding is not specified as an integer
        card_enc = _require_pysat_cardenc()
        return _pysat_cardinality_constraints(cons_vars, cons_value, encoding, card_enc.atmost, "atmost")
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for SUM_AT_MOST constraint.")

def gen_constraints_at_least(model_type, cons_vars, cons_value):
    if model_type == "milp":
        return [f"{cons_vars[i]} >= {cons_value}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 1:
        return [f"{cons_vars[i]}" for i in range(len(cons_vars))]
    elif model_type == "sat" and cons_value == 0:
        return []
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for GREATER_EQUAL constraint.")

def gen_constraints_sum_at_least(model_type, cons_vars, cons_value, encoding=1):
    if model_type == "milp":
        return [' + '.join(f"{cons_vars[i]}" for i in range(len(cons_vars))) + f" >= {cons_value}"]
    elif model_type == "sat" and cons_value == 1:
        return [' '.join(f"{cons_vars[i]}" for i in range(len(cons_vars)))]
    elif model_type == "sat" and pysat_import:
        card_enc = _require_pysat_cardenc()
        return _pysat_cardinality_constraints(cons_vars, cons_value, encoding, card_enc.atleast, "atleast")
    else:
        raise ValueError(f"Unsupported model_type '{model_type}' for SUM_GREATER_EQUAL constraint.")

def gen_sequential_encoding_sat(hw_list, weight, dummy_variables=None):
    return search_constraints.gen_sequential_encoding_sat(hw_list, weight, dummy_variables)

# ----------- Matsui's branch-and-bound constraints Generation -------------
def gen_matsui_constraints_milp(Round, best_obj, obj_fun, cons_type="ALL"):
    return search_constraints.gen_matsui_constraints_milp(
        Round,
        best_obj,
        obj_fun,
        cons_type,
        predefined_constraint_factory=gen_predefined_constraints,
    )


def gen_matsui_constraints_sat(Round, best_obj, obj_sat, obj_var, GroupConstraintChoice=1, GroupNumForChoice=1):
    return search_constraints.gen_matsui_constraints_sat(
        Round,
        best_obj,
        obj_sat,
        obj_var,
        GroupConstraintChoice,
        GroupNumForChoice,
    )


def gen_matsui_partial_cardinality_sat(obj_var, dummy_var, k, left, right, m):
    return search_constraints.gen_matsui_partial_cardinality_sat(
        obj_var,
        dummy_var,
        k,
        left,
        right,
        m,
    )


def gen_xor_constraints(vin1, vin2, vout, model_type, v_dummy=None, version=0):
    return bit_constraints.gen_xor_constraints(vin1, vin2, vout, model_type, v_dummy, version)

def gen_word_xor_constraints(vin1, vin2, vout, model_type, v_dummy=None, version=0):
    return bit_constraints.gen_word_xor_constraints(vin1, vin2, vout, model_type, v_dummy, version)


def gen_nxor_constraints(vin, vout, model_type, v_dummy=None, version=0):
    return bit_constraints.gen_nxor_constraints(vin, vout, model_type, v_dummy, version)

def gen_word_nxor_constraints(vin, vout, model_type, v_dummy=None, version=0):
    return bit_constraints.gen_word_nxor_constraints(vin, vout, model_type, v_dummy, version)

def gen_matrix_constraints(vin, vout, model_type, v_dummy=None):
    return bit_constraints.gen_matrix_constraints(vin, vout, model_type, v_dummy)

def gen_word_matrix_constraints(vin, vout, model_type, v_dummy=None):
    return bit_constraints.gen_word_matrix_constraints(vin, vout, model_type, v_dummy)


# ---------------- Common utilities in SAT and MILP modeling ---------------- #
def generate_and_save_constraints(
    model_type,
    tool_type,
    mode,
    ttable,
    input_variables,
    output_variables,
    weight_variables=None,
    objective_fun=None,
    model_filename=None,
):
    return model_templates.generate_and_save_constraints(
        model_type,
        tool_type,
        mode,
        ttable,
        input_variables,
        output_variables,
        weight_variables=weight_variables,
        objective_fun=objective_fun,
        model_filename=model_filename,
    )


def _load_constraints_template_cached(filename, mtime_ns):
    return model_templates.load_constraints_template_cached(filename, mtime_ns)


def load_constraints_template(filename):
    return model_templates.load_constraints_template(filename)


def _build_template_replacer(*template_var_groups):
    return model_templates.build_template_replacer(*template_var_groups)


def gen_constraints_obj_func_from_template(filename, var_in, var_out, var_p=None):
    return model_templates.gen_constraints_obj_func_from_template(filename, var_in, var_out, var_p)


def inequality_to_constraint_sat(inequality, variables):
    return model_templates.inequality_to_constraint_sat(inequality, variables)


def inequality_to_constraint_milp(inequality, variables):
    return model_templates.inequality_to_constraint_milp(inequality, variables)
