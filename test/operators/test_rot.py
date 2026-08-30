import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # this file -> test -> <ROOT>
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import variables.variables as var
from operators.operators import Rot
import tools.milp_search as milp_search
import tools.sat_search as sat_search
import solving.solving as solving

FILES_DIR = ROOT / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)


_LOG = sys.stdout


def log(*args):
    print(*args, file=_LOG)


def rotated_pairs(op):
    # Rotation equivalence pairs, matching Rot.generate_model:
    #   'r': in[i] == out[(i+amount)%n];  'l': in[(i+amount)%n] == out[i]
    var_in = op.get_var_model("in", 0)
    var_out = op.get_var_model("out", 0)
    n = len(var_in)
    amount = op.amount
    if op.direction == 'r':
        left = list(var_in)
        right = [var_out[(i + amount) % n] for i in range(n)]
    else:
        left = [var_in[(i + amount) % n] for i in range(n)]
        right = list(var_out)
    return left, right


def expected_solution_count(model_version, bitsize, name="Rot"):
    # Rot is a bijection, so every version has 2 ** bitsize solutions.
    # Explicit lists + else:raise so an undeclared version fails loudly.
    if model_version in [f"{name}_XORDIFF", f"{name}_LINEAR"]:
        return 2 ** bitsize
    elif model_version == f"{name}_INTEGRAL_TWOSUBSET":  # milp-only
        return 2 ** bitsize
    else:
        raise AssertionError(f"unhandled model_version {model_version}")


def print_solutions(op, sol_list):
    # Print each solution as [input] -> [output] (bit values read from the solution dict,
    # bit-level or word-level to match the model_version).
    bitwise = "TRUNCATED" not in op.model_version
    for sol in sol_list:
        ins = ",".join("".join(str(round(float(sol[b]))) for b in op.get_var_model("in", i, bitwise=bitwise))
                       for i in range(len(op.input_vars)))
        outs = ",".join("".join(str(round(float(sol[b]))) for b in op.get_var_model("out", i, bitwise=bitwise))
                        for i in range(len(op.output_vars)))
        log(f"  [{ins}] -> [{outs}]")


def check_solutions(op, sol_list):
    # Every solution must satisfy the rotation relation left[i] == right[i] (see rotated_pairs).
    # Explicit lists + else:raise so an undeclared version fails loudly.
    name = op.__class__.__name__
    if op.model_version in [f"{name}_XORDIFF", f"{name}_LINEAR"]:
        left, right = rotated_pairs(op)
    elif op.model_version == f"{name}_INTEGRAL_TWOSUBSET":  # milp-only
        left, right = rotated_pairs(op)
    else:
        raise AssertionError(f"unhandled model_version {op.model_version}")
    # sol is a dict {var_name: value}; normalize MILP float/-0.0 & SAT int.
    for sol in sol_list:
        for a, b in zip(left, right):
            av, bv = round(float(sol[a])), round(float(sol[b]))
            assert av == bv, f"{op.model_version} dir={op.direction}: {a}={av} != {b}={bv} in solution {sol}"


def gen_operator(bitsize=4, direction='l', amount=1):
    log("\n********************* operation: Rot ********************* ")
    my_input, my_output = [var.Variable(bitsize, ID="in")], [var.Variable(bitsize, ID="out")]
    op = Rot(my_input, my_output, direction=direction, amount=amount, ID='Rot')  # rotate by left/right
    op.display()
    return op


def test_implementation(op):
    bitsize = op.input_vars[0].bitsize
    macro = "ROTR" if op.direction == 'r' else "ROTL"

    code = op.generate_implementation(implementation_type="python", unroll=True)
    log(f"python code with unroll=True: \n", "\n".join(code))
    assert code == [f"out = {macro}(in, {op.amount}, {bitsize})"], f"python implementation: {code}"

    code = op.generate_implementation(implementation_type="c", unroll=True)
    log(f"c code with unroll=True: \n", "\n".join(code))
    assert code == [f"out = {macro}(in, {op.amount}, {bitsize});"], f"c implementation: {code}"

    code = op.generate_implementation(implementation_type="verilog", unroll=True)
    log(f"verilog code with unroll=True: \n", "\n".join(code))
    assert code == [f"assign out = `{macro}(in, {op.amount}, {bitsize});"], f"verilog implementation: {code}"


def test_milp_model(op):
    model_versions = [op.__class__.__name__ + "_XORDIFF", op.__class__.__name__ + "_LINEAR", op.__class__.__name__ + "_INTEGRAL_TWOSUBSET"]
    for model_v in model_versions:
        op.model_version = model_v
        milp_constraints = op.generate_model(model_type='milp')
        log(f"MILP constraints with model_version={model_v}: \n", "\n".join(milp_constraints))
        filename = str(FILES_DIR / f"milp_{op.ID}_{model_v}.lp")
        model = milp_search.write_milp_model(constraints=milp_constraints, filename=filename)
        sol_list = solving.solve_milp(filename, {"solution_number": 100000})
        log(f"Number of solutions: {len(sol_list)}")
        print_solutions(op, sol_list)
        expected = expected_solution_count(model_v, op.input_vars[0].bitsize)
        assert len(sol_list) == expected, f"{model_v}: MILP has {len(sol_list)} solutions, expected {expected}"
        check_solutions(op, sol_list)


def test_sat_model(op):
    model_versions = [op.__class__.__name__ + "_XORDIFF", op.__class__.__name__ + "_LINEAR"]
    solver = None  # Change to test different solvers supported for solving SAT problems
    for model_v in model_versions:
        op.model_version = model_v
        sat_constraints = op.generate_model(model_type='sat')
        log(f"SAT constraints with model_version={model_v}: \n", "\n".join(sat_constraints))
        if solver == "CPSAT":
            family_of_variables = ' '.join(sat_constraints).replace('-', '')
            all_variables = sorted(set(family_of_variables.split()))
            variable_dict = {variable: i + 1 for (i, variable) in enumerate(all_variables)}
            sol_list = solving.solve_sat_cpsat(sat_constraints, variable_dict, {"solution_number": 100000})
        else:
            filename = str(FILES_DIR / f"sat_{op.ID}_{model_v}.cnf")
            model = sat_search.write_sat_model(constraints=sat_constraints, filename=filename)
            log("variable_map in sat:\n", model["variable_map"])
            sol_list = solving.solve_sat(filename, model["variable_map"], {"solution_number": 100000})
        log(f"Number of solutions: {len(sol_list)}")
        print_solutions(op, sol_list)
        expected = expected_solution_count(model_v, op.input_vars[0].bitsize)
        assert len(sol_list) == expected, f"{model_v}: SAT has {len(sol_list)} solutions, expected {expected}"
        check_solutions(op, sol_list)


def test_rot(bitsize, direction, amount):

    op = gen_operator(bitsize=bitsize, direction=direction, amount=amount)

    test_implementation(op)

    test_milp_model(op)   # INTEGRAL_TWOSUBSET is included in the MILP loop

    test_sat_model(op)


if __name__ == '__main__':
    log_path = FILES_DIR / "test_rot_log.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log(f"=== Implementation Test Log ===")

        for bitsize in (2, 3, 4):
            for direction in ('l', 'r'):
                test_rot(bitsize=bitsize, direction=direction, amount=1)

        log("All implementation tests completed!")
    print(f"log written to {log_path}")
