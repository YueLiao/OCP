"""Small command-line profiler for OCP model generation.

The profiler builds constraints only; it does not call MILP/SAT solvers.
"""

import argparse
import json
import time

from attacks.common import parse_and_set_configs
from tools.model_constraints import gen_round_model_constraint_obj_fun


DEFAULT_CASES = ("present:1", "chacha:1", "salsa:1", "forro:1")


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
        return case, None
    name, rounds = case.split(":", 1)
    return name, int(rounds)


def profile_case(case, goal="DIFFERENTIALPATH_PROB", model_type="sat", top_limit=8):
    """Profile model generation for one primitive case.

    Args:
        case: Case string in the form ``name`` or ``name:rounds``.
        goal: OCP cryptanalysis goal passed to model configuration.
        model_type: Model backend type such as ``sat`` or ``milp``.
        top_limit: Number of hotspot rows to expose in summary fields.

    Returns:
        dict: JSON-serializable timing and constraint statistics.
    """

    name, rounds = _parse_case(case)
    factory = _cipher_factory(name)

    build_start = time.perf_counter()
    cipher = factory(r=rounds)
    build_time_s = time.perf_counter() - build_start

    config_model, _ = parse_and_set_configs(
        cipher,
        goal,
        "EXISTENCE",
        {"model_type": model_type, "profile_model_generation": True, "verbose": False},
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
    return {
        "case": case,
        "cipher": cipher.name,
        "rounds": cipher.functions["PERMUTATION"].nbr_rounds,
        "model_type": model_type,
        "goal": goal,
        "build_time_s": round(build_time_s, 6),
        "generation_time_s": round(generation_time_s, 6),
        "constraint_count": len(constraints),
        "objective_rows": len(objective),
        "top_operators": top_operators,
        "top_operator_prefixes": top_operator_prefixes,
        "profile": profile,
    }


def profile_cases(cases=DEFAULT_CASES, goal="DIFFERENTIALPATH_PROB", model_type="sat", top_limit=8):
    return [
        profile_case(case, goal=goal, model_type=model_type, top_limit=top_limit)
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
    parser.add_argument("--indent", type=int, default=2)
    args = parser.parse_args(argv)

    print(
        json.dumps(
            profile_cases(
                args.cases,
                goal=args.goal,
                model_type=args.model_type,
                top_limit=args.top_limit,
            ),
            indent=args.indent,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
