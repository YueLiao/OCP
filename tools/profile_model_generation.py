"""Small command-line profiler for OCP model generation.

The profiler builds constraints only; it does not call MILP/SAT solvers.
"""

import argparse
import json
import time

from attacks.common import parse_and_set_configs
from tools.model_constraints import gen_round_model_constraint_obj_fun


DEFAULT_CASES = ("present:1", "chacha:1", "salsa:1", "forro:1")
NON_ELIDABLE_EQUAL_PREFIXES = (
    "Equal:IN_LINK",
    "Equal:OUT_LINK",
    "Equal:LINK_EQ",
)


def _top_profile_entries(entries, limit):
    sorted_entries = sorted(
        entries.items(),
        key=lambda item: (-item[1]["constraints"], -item[1]["calls"], item[0]),
    )
    return [
        {
            "name": name,
            "calls": stats["calls"],
            "constraints": stats["constraints"],
            "time_s": stats["time_s"],
        }
        for name, stats in sorted_entries[:limit]
    ]


def _is_identity_elision_candidate(prefix_name):
    return prefix_name.startswith("Equal:") and not prefix_name.startswith(
        NON_ELIDABLE_EQUAL_PREFIXES
    )


def summarize_identity_elision_candidates(profile, top_limit=8):
    """Estimate internal identity-equivalence constraints that may be elidable.

    This is a conservative diagnostic. It does not remove constraints; it only
    groups internal Equal constraints by ID prefix so a later graph-level
    identity-elision pass can be designed against measured hotspots.
    """

    candidates = {
        name: stats
        for name, stats in profile.get("operator_prefixes", {}).items()
        if _is_identity_elision_candidate(name)
    }
    estimated_constraints = sum(stats["constraints"] for stats in candidates.values())
    total_constraints = profile.get("total_constraints", 0)
    ratio = estimated_constraints / total_constraints if total_constraints else 0.0
    return {
        "estimated_constraints": estimated_constraints,
        "estimated_ratio": round(ratio, 6),
        "top_candidates": _top_profile_entries(candidates, top_limit),
    }


def _cipher_factory(name):
    normalized = name.lower()
    if normalized == "present":
        from primitives.present import PRESENT_PERMUTATION

        return PRESENT_PERMUTATION
    if normalized == "forro":
        from primitives.forro import FORRO_PERMUTATION

        return FORRO_PERMUTATION
    if normalized == "chacha":
        from primitives.chacha import CHACHA_PERMUTATION

        return CHACHA_PERMUTATION
    if normalized == "salsa":
        from primitives.salsa import SALSA_PERMUTATION

        return SALSA_PERMUTATION
    raise ValueError(
        f"Unknown profile case '{name}'. Supported cases: present, chacha, salsa, forro."
    )


def _parse_case(case):
    if ":" not in case:
        if not case:
            raise ValueError("Profile case name cannot be empty.")
        return case, None
    name, rounds = case.split(":", 1)
    if not name:
        raise ValueError(f"Invalid profile case '{case}': primitive name cannot be empty.")
    try:
        parsed_rounds = int(rounds)
    except ValueError as exc:
        raise ValueError(
            f"Invalid profile case '{case}': rounds must be a positive integer."
        ) from exc
    if parsed_rounds <= 0:
        raise ValueError(
            f"Invalid profile case '{case}': rounds must be a positive integer."
        )
    return name, parsed_rounds


def profile_case(case, goal="DIFFERENTIALPATH_PROB", model_type="sat", top_limit=8, identity_elision=False):
    """Profile model generation for one primitive case.

    Args:
        case: Case string in the form ``name`` or ``name:rounds``.
        goal: OCP cryptanalysis goal passed to model configuration.
        model_type: Model backend type such as ``sat`` or ``milp``.
        top_limit: Number of hotspot rows to expose in summary fields.
        identity_elision: Whether to enable the opt-in alias prototype.

    Returns:
        dict: JSON-serializable timing and constraint statistics.
    """

    if top_limit <= 0:
        raise ValueError("top_limit must be a positive integer.")
    name, rounds = _parse_case(case)
    factory = _cipher_factory(name)

    build_start = time.perf_counter()
    cipher = factory(r=rounds)
    build_time_s = time.perf_counter() - build_start

    config_model, _ = parse_and_set_configs(
        cipher,
        goal,
        "EXISTENCE",
        {
            "model_type": model_type,
            "profile_model_generation": True,
            "verbose": False,
            "identity_elision": identity_elision,
        },
        {"verbose": False},
    )

    generation_start = time.perf_counter()
    constraints, objective = gen_round_model_constraint_obj_fun(
        cipher,
        goal,
        model_type,
        config_model,
    )
    generation_time_s = time.perf_counter() - generation_start

    profile = config_model["model_generation_profile"]
    top_operators = _top_profile_entries(profile["operators"], top_limit)
    top_operator_prefixes = _top_profile_entries(profile["operator_prefixes"], top_limit)
    identity_candidates = summarize_identity_elision_candidates(profile, top_limit=top_limit)
    report = {
        "case": case,
        "cipher": cipher.name,
        "rounds": cipher.functions["PERMUTATION"].nbr_rounds,
        "model_type": model_type,
        "goal": goal,
        "identity_elision": identity_elision,
        "build_time_s": round(build_time_s, 6),
        "generation_time_s": round(generation_time_s, 6),
        "constraint_count": len(constraints),
        "objective_rows": len(objective),
        "top_operators": top_operators,
        "top_operator_prefixes": top_operator_prefixes,
        "identity_elision_candidates": identity_candidates,
        "profile": profile,
    }
    if identity_elision:
        report["identity_elision_profile"] = config_model["identity_elision_profile"]
    return report


def profile_cases(
    cases=DEFAULT_CASES,
    goal="DIFFERENTIALPATH_PROB",
    model_type="sat",
    top_limit=8,
    identity_elision=False,
):
    return [
        profile_case(
            case,
            goal=goal,
            model_type=model_type,
            top_limit=top_limit,
            identity_elision=identity_elision,
        )
        for case in cases
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description="Profile OCP model generation without solving.")
    parser.add_argument(
        "cases",
        nargs="*",
        default=list(DEFAULT_CASES),
        help="Primitive cases such as present:1 or forro:1.",
    )
    parser.add_argument("--goal", default="DIFFERENTIALPATH_PROB")
    parser.add_argument("--model-type", default="sat")
    parser.add_argument("--top-limit", type=int, default=8)
    parser.add_argument("--identity-elision", action="store_true")
    parser.add_argument("--indent", type=int, default=2)
    args = parser.parse_args(argv)

    try:
        reports = profile_cases(
            args.cases,
            goal=args.goal,
            model_type=args.model_type,
            top_limit=args.top_limit,
            identity_elision=args.identity_elision,
        )
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(reports, indent=args.indent, sort_keys=True))


if __name__ == "__main__":
    main()
