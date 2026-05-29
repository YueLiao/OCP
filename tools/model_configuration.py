"""Cipher model scope, version assignment, and round model generation."""

from tools.model_generation_state import (
    IDENTITY_ELISION_ALIASES_KEY,
    apply_identity_aliases,
    configure_identity_elision,
    generate_model_with_profile,
    reset_model_generation_profile,
)


GOAL_MODEL_VERSION_RULES = {
    "DIFFERENTIAL_SBOXCOUNT": (("XORDIFF", None), ("XORDIFF_A", "Sbox")),
    "DIFFERENTIALPATH_PROB": (("XORDIFF", None), ("XORDIFF_PR", "Sbox")),
    "DIFFERENTIAL_PROB": (("XORDIFF", None), ("XORDIFF_PR", "Sbox")),
    "LINEAR_SBOXCOUNT": (("LINEAR", None), ("LINEAR_A", "Sbox")),
    "LINEARPATH_CORR": (("LINEAR", None), ("LINEAR_PR", "Sbox")),
    "LINEARHULL_CORR": (("LINEAR", None), ("LINEAR_PR", "Sbox")),
    "TRUNCATEDDIFF_SBOXCOUNT": (("TRUNCATEDDIFF", None), ("TRUNCATEDDIFF_A", "Sbox")),
    "TRUNCATEDLINEAR_SBOXCOUNT": (
        ("TRUNCATEDLINEAR", None),
        ("TRUNCATEDLINEAR_A", "Sbox"),
    ),
}


def fill_functions_rounds_layers_positions(
    cipher,
    functions=None,
    rounds=None,
    layers=None,
    positions=None,
):
    """
    Fill missing model scope fields with full cipher coverage.

    Returns:
        tuple: (functions, rounds, layers, positions)
    """
    if functions is None:
        functions = [f for f in cipher.functions]
    if rounds is None:
        rounds = {f: list(range(1, cipher.functions[f].nbr_rounds + 1)) for f in functions}
    if layers is None:
        layers = {
            f: {r: list(range(cipher.functions[f].nbr_layers+1)) for r in rounds[f]}
            for f in functions
        }
    if positions is None:
        positions = {
            f: {
                r: {
                    l: list(range(len(cipher.functions[f].constraints[r][l])))
                    for l in layers[f][r]
                }
                for r in rounds[f]
            }
            for f in functions
        }
    return functions, rounds, layers, positions


def configure_model_version(
    cipher,
    goal,
    config_model,
    set_versions=None,
):
    functions = config_model.get("functions")
    rounds = config_model.get("rounds")
    layers = config_model.get("layers")
    positions = config_model.get("positions")
    set_versions = set_versions or set_model_versions

    if goal not in GOAL_MODEL_VERSION_RULES:
        raise ValueError(f"Invalid goal: {goal}.")

    for version, operator_name in GOAL_MODEL_VERSION_RULES[goal]:
        set_versions(
            cipher,
            version,
            functions,
            rounds,
            layers,
            positions,
            operator_name=operator_name,
        )

    if "model_version" in config_model:
        model_version = config_model.get("model_version")
        version = model_version.get("model_version")
        operator_name = model_version.get("operator_name", None)
        set_versions(
            cipher,
            version,
            functions,
            rounds,
            layers,
            positions,
            operator_name=operator_name,
        )


def set_model_versions(cipher, version, functions, rounds, layers, positions, operator_name=None):
    """Assign a model version to matching constraints in the selected cipher scope."""
    def assign_version(cons):
        if operator_name is None:
            cons.model_version = cons.__class__.__name__ + "_" + version
        elif operator_name == cons.__class__.__name__ or (
            operator_name == "Sbox"
            and cons.__class__.__name__.endswith("Sbox")
        ):
            cons.model_version = cons.__class__.__name__ + "_" + version

    for cons in cipher.inputs_constraints:
        assign_version(cons)
    for cons in cipher.outputs_constraints:
        assign_version(cons)

    for f in functions:
        for r in rounds[f]:
            for l in layers[f][r]:
                for cons in cipher.functions[f].constraints[r][l]:
                    assign_version(cons)


def gen_round_model_constraint_obj_fun(
    cipher,
    goal,
    model_type,
    config_model,
    configure_versions=configure_model_version,
    reset_profile=reset_model_generation_profile,
    configure_identity=configure_identity_elision,
    generate_with_profile=generate_model_with_profile,
    apply_aliases=apply_identity_aliases,
):
    """Generate constraints and objective-function variables for selected rounds."""
    configure_versions(cipher, goal, config_model)
    reset_profile(config_model)
    configure_identity(cipher, config_model)
    constraint = []
    obj_fun = [[] for _ in range(cipher.functions["PERMUTATION"].nbr_rounds)]

    for cons in cipher.inputs_constraints:
        constraint.extend(generate_with_profile(cons, model_type, config_model))
    for cons in cipher.outputs_constraints:
        constraint.extend(generate_with_profile(cons, model_type, config_model))

    functions = config_model.get("functions")
    rounds = config_model.get("rounds")
    layers = config_model.get("layers")
    positions = config_model.get("positions")
    for f in functions:
        for r in rounds[f]:
            for l in layers[f][r]:
                for i in positions[f][r][l]:
                    cons = cipher.functions[f].constraints[r][l][i]
                    cons_class_name = cons.__class__.__name__
                    params = (config_model.get("model_params") or {}).get(cons_class_name, {})
                    constraint.extend(
                        generate_with_profile(cons, model_type, config_model, **params)
                    )
                    if hasattr(cons, 'weight'):
                        aliases = config_model.get(IDENTITY_ELISION_ALIASES_KEY) or {}
                        obj_fun[r-1].extend(apply_aliases(cons.weight, aliases))
    return constraint, obj_fun
