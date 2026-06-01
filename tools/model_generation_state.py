"""State helpers for model generation profiling and identity elision."""

import re
import time


IDENTITY_ELISION_ALIASES_KEY = "_identity_elision_aliases"
IDENTITY_ELISION_PROFILE_KEY = "identity_elision_profile"
MODEL_GENERATION_PROFILE_ENABLED_KEY = "profile_model_generation"
MODEL_GENERATION_PROFILE_KEY = "model_generation_profile"

_MODEL_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_])(-?)([A-Za-z][A-Za-z0-9_]*)(?![A-Za-z0-9_])")
_NON_ELIDABLE_EQUAL_PREFIXES = (
    "Equal:IN_LINK",
    "Equal:OUT_LINK",
    "Equal:LINK_EQ",
)


def reset_model_generation_profile(config_model):
    if config_model.get(MODEL_GENERATION_PROFILE_ENABLED_KEY):
        config_model[MODEL_GENERATION_PROFILE_KEY] = {
            "total_constraints": 0,
            "total_time_s": 0.0,
            "operators": {},
            "operator_prefixes": {},
        }


def profile_operator_prefix(cons, operator_name):
    operator_id = getattr(cons, "ID", None)
    if not operator_id:
        return operator_name
    return re.sub(r"(?:_\d+)+$", "", operator_id)


def identity_elision_prefix_key(cons):
    operator_name = cons.__class__.__name__
    return f"{operator_name}:{profile_operator_prefix(cons, operator_name)}"


def is_identity_elision_candidate(cons):
    prefix_key = identity_elision_prefix_key(cons)
    return (
        _identity_equal_edge(cons) is not None
        and prefix_key.startswith("Equal:")
        and not prefix_key.startswith(_NON_ELIDABLE_EQUAL_PREFIXES)
    )


def _identity_equal_edge(cons):
    if cons.__class__.__name__ != "Equal":
        return None
    if len(getattr(cons, "input_vars", [])) != 1 or len(getattr(cons, "output_vars", [])) != 1:
        return None
    input_var = cons.input_vars[0]
    output_var = cons.output_vars[0]
    if getattr(input_var, "bitsize", None) != getattr(output_var, "bitsize", None):
        return None
    return input_var.ID, output_var.ID


def resolve_identity_alias(aliases, var_id):
    seen = set()
    while var_id in aliases:
        if var_id in seen:
            raise ValueError(f"Identity elision alias cycle detected at '{var_id}'.")
        seen.add(var_id)
        var_id = aliases[var_id]
    return var_id


def build_identity_elision_aliases(cipher, config_model):
    aliases = {}
    functions, rounds, layers, positions = (
        config_model.get("functions"),
        config_model.get("rounds"),
        config_model.get("layers"),
        config_model.get("positions"),
    )
    for f in functions:
        for r in rounds[f]:
            for l in layers[f][r]:
                for i in positions[f][r][l]:
                    cons = cipher.functions[f].constraints[r][l][i]
                    edge = _identity_equal_edge(cons)
                    if edge is None or not is_identity_elision_candidate(cons):
                        continue
                    input_id, output_id = edge
                    if input_id == output_id:
                        continue
                    existing = aliases.get(output_id)
                    if existing is not None and existing != input_id:
                        raise ValueError(
                            "Identity elision alias conflict for "
                            f"'{output_id}': '{existing}' vs '{input_id}'."
                        )
                    aliases[output_id] = input_id
    return {
        var_id: resolve_identity_alias(aliases, target)
        for var_id, target in aliases.items()
    }


def rewrite_token_with_alias(token, aliases, cache=None):
    if cache is not None and token in cache:
        return cache[token]
    parts = token.split("_")
    for index in range(len(parts), 0, -1):
        source = "_".join(parts[:index])
        if source in aliases:
            suffix = "_".join(parts[index:])
            rewritten = aliases[source] if not suffix else aliases[source] + "_" + suffix
            if cache is not None:
                cache[token] = rewritten
            return rewritten
    if cache is not None:
        cache[token] = token
    return token


def apply_identity_aliases_to_line(line, aliases, token_cache=None):
    if not aliases:
        return line

    def replace(match):
        sign, token = match.groups()
        return sign + rewrite_token_with_alias(token, aliases, cache=token_cache)

    return _MODEL_TOKEN_RE.sub(replace, line)


def apply_identity_aliases(model_lines, aliases):
    if not aliases:
        return model_lines
    token_cache = {}
    return [
        apply_identity_aliases_to_line(line, aliases, token_cache=token_cache)
        for line in model_lines
    ]


def configure_identity_elision(cipher, config_model):
    if not config_model.get("identity_elision"):
        config_model.pop(IDENTITY_ELISION_ALIASES_KEY, None)
        config_model.pop(IDENTITY_ELISION_PROFILE_KEY, None)
        return
    aliases = build_identity_elision_aliases(cipher, config_model)
    config_model[IDENTITY_ELISION_ALIASES_KEY] = aliases
    config_model[IDENTITY_ELISION_PROFILE_KEY] = {
        "aliases": len(aliases),
        "skipped_constraints": 0,
    }


def update_profile_bucket(bucket, generated_count, elapsed_s):
    bucket["calls"] += 1
    bucket["constraints"] += generated_count
    bucket["time_s"] = round(bucket["time_s"] + elapsed_s, 6)


def record_model_generation_profile(config_model, cons, generated_count, elapsed_s):
    if not config_model.get(MODEL_GENERATION_PROFILE_ENABLED_KEY):
        return
    operator_name = cons.__class__.__name__
    profile = config_model[MODEL_GENERATION_PROFILE_KEY]
    profile["total_constraints"] += generated_count
    profile["total_time_s"] = round(profile["total_time_s"] + elapsed_s, 6)
    operator_profile = profile["operators"].setdefault(
        operator_name,
        {"calls": 0, "constraints": 0, "time_s": 0.0},
    )
    update_profile_bucket(operator_profile, generated_count, elapsed_s)

    prefix_key = f"{operator_name}:{profile_operator_prefix(cons, operator_name)}"
    prefix_profile = profile["operator_prefixes"].setdefault(
        prefix_key,
        {"calls": 0, "constraints": 0, "time_s": 0.0},
    )
    update_profile_bucket(prefix_profile, generated_count, elapsed_s)


def generate_model_with_profile(cons, model_type, config_model, **params):
    aliases = config_model.get(IDENTITY_ELISION_ALIASES_KEY) or {}
    if aliases and is_identity_elision_candidate(cons):
        record_model_generation_profile(config_model, cons, 0, 0.0)
        config_model[IDENTITY_ELISION_PROFILE_KEY]["skipped_constraints"] += 1
        return []

    time_start = time.perf_counter()
    generated = cons.generate_model(model_type=model_type, **params)
    elapsed_s = time.perf_counter() - time_start
    generated = apply_identity_aliases(generated, aliases)
    record_model_generation_profile(
        config_model,
        cons,
        len(generated),
        elapsed_s,
    )
    return generated
