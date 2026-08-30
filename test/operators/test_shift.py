import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # this file -> test -> <ROOT>
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import variables.variables as var
from operators.operators import Shift
import tools.milp_search as milp_search
import tools.sat_search as sat_search
import solving.solving as solving

FILES_DIR = ROOT / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

_LOG = sys.stdout


def log(*args):
    print(*args, file=_LOG)


def expected_solution_count(op):
    # Exactly `bitsize` bits stay free either way, so 2**bitsize solutions (indep. of direction/amount).
    # Explicit per-version branches so an undeclared future model_version fails loudly.
    name = op.__class__.__name__
    bitsize = op.input_vars[0].bitsize
    if op.model_version == f"{name}_XORDIFF":
        return 2 ** bitsize
    elif op.model_version == f"{name}_LINEAR":
        return 2 ** bitsize
    else:
        raise AssertionError(f"unhandled model_version {op.model_version}")


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
    # Each solution must satisfy the shift relation: window bits equal src->dst, zero-filled bits 0,
    # remaining bits free. Explicit per-version branches so an undeclared future model_version fails loudly.
    name = op.__class__.__name__
    var_in, var_out = op.get_var_model("in", 0), op.get_var_model("out", 0)
    n, s = len(var_in), op.amount

    if op.model_version == f"{name}_XORDIFF":
        # XORDIFF zeroes the OUTPUT side.
        if op.direction == 'r':
            eq_pairs = [(var_in[i], var_out[i + s]) for i in range(n - s)]  # in[i] -> out[i+s]
            zero_vars = [var_out[i] for i in range(s)]                      # zero-filled top output bits
        else:  # 'l'
            eq_pairs = [(var_in[i + s], var_out[i]) for i in range(n - s)]  # in[i+s] -> out[i]
            zero_vars = [var_out[i] for i in range(n - s, n)]              # zero-filled low output bits
    elif op.model_version == f"{name}_LINEAR":
        # LINEAR zeroes the INPUT side (dual).
        if op.direction == 'r':
            eq_pairs = [(var_in[i], var_out[i + s]) for i in range(n - s)]  # in[i] -> out[i+s]
            zero_vars = [var_in[i] for i in range(n - s, n)]              # forced-zero low input bits
        else:  # 'l'
            eq_pairs = [(var_in[i + s], var_out[i]) for i in range(n - s)]  # in[i+s] -> out[i]
            zero_vars = [var_in[i] for i in range(s)]                      # forced-zero top input bits
    else:
        raise AssertionError(f"unhandled model_version {op.model_version}")

    for sol in sol_list:
        for src, dst in eq_pairs:
            sv, dv = round(float(sol[src])), round(float(sol[dst]))  # normalize MILP float/-0.0 & SAT int
            assert sv == dv, f"{op.model_version}/{op.direction}: {src}={sv} != {dst}={dv} in solution {sol}"
        for z in zero_vars:
            zv = round(float(sol[z]))
            assert zv == 0, f"{op.model_version}/{op.direction}: {z}={zv} must be 0 in solution {sol}"


def gen_operator(bitsize=4, direction='l', amount=1):
    log("\n********************* operation: Shift ********************* ")
    my_input, my_output = [var.Variable(bitsize, ID="in")], [var.Variable(bitsize, ID="out")]
    op = Shift(my_input, my_output, direction=direction, amount=amount, ID='Shift')  # shift by left/right
    op.display()
    return op


def test_implementation(op):
    code = op.generate_implementation(implementation_type="python", unroll=True)
    log(f"python code with unroll=True: \n", "\n".join(code))
    shift_operator = ">>" if op.direction == 'r' else "<<"
    bitsize = op.input_vars[0].bitsize
    assert code == [f"out = (in {shift_operator} {op.amount}) & (2**{bitsize} - 1)"], f"python implementation: {code}"

    code = op.generate_implementation(implementation_type="c", unroll=True)
    log(f"c code with unroll=True: \n", "\n".join(code))
    assert code == [f"out = (in {shift_operator} {op.amount}) & ((1<<{bitsize}) - 1);"], f"c implementation: {code}"

    code = op.generate_implementation(implementation_type="verilog", unroll=True)
    log(f"verilog code with unroll=True: \n", "\n".join(code))
    assert code == [f"assign out = (in {shift_operator} {op.amount}) & ((1<<{bitsize}) - 1);"], f"verilog implementation: {code}"


def test_milp_model(op):
    model_versions = [op.__class__.__name__ + "_XORDIFF", op.__class__.__name__ + "_LINEAR"]
    for model_v in model_versions:
        op.model_version = model_v
        milp_constraints = op.generate_model(model_type='milp')
        log(f"MILP constraints with model_version={model_v}: \n", "\n".join(milp_constraints))
        filename = str(FILES_DIR / f"milp_{op.ID}_{op.direction}_{model_v}.lp")
        model = milp_search.write_milp_model(constraints=milp_constraints, filename=filename)
        sol_list = solving.solve_milp(filename, {"solution_number": 100000})
        log(f"Number of solutions: {len(sol_list)}")
        print_solutions(op, sol_list)
        expected = expected_solution_count(op)
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
            filename = str(FILES_DIR / f"sat_{op.ID}_{op.direction}_{model_v}.cnf")
            model = sat_search.write_sat_model(constraints=sat_constraints, filename=filename)
            log("variable_map in sat:\n", model["variable_map"])
            sol_list = solving.solve_sat(filename, model["variable_map"], {"solution_number": 100000})
        log(f"Number of solutions: {len(sol_list)}")
        print_solutions(op, sol_list)
        expected = expected_solution_count(op)
        assert len(sol_list) == expected, f"{model_v}: SAT has {len(sol_list)} solutions, expected {expected}"
        check_solutions(op, sol_list)


def test_shift(bitsize, direction, amount):

    op = gen_operator(bitsize=bitsize, direction=direction, amount=amount)

    test_implementation(op)

    test_milp_model(op)

    test_sat_model(op)


if __name__ == '__main__':
    log_path = FILES_DIR / "test_shift_log.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log("=== Implementation Test Log ===")

        test_shift(bitsize=2, direction='l', amount=1)
        test_shift(bitsize=2, direction='r', amount=1)
        test_shift(bitsize=4, direction='l', amount=1)
        test_shift(bitsize=4, direction='r', amount=1)

        log("All implementation tests completed!")

    print(f"log written to {log_path}")
