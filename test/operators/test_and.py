import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # this file -> test -> <ROOT>
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import variables.variables as var
from operators.boolean_operators import AND
import tools.milp_search as milp_search
import tools.sat_search as sat_search
import solving.solving as solving

FILES_DIR = ROOT / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

_LOG = sys.stdout


def log(*args):
    print(*args, file=_LOG)


def expected_solution_count(op):
    # AND is nonlinear: each bit contributes a fixed number of valid (in0,in1,out[,p]) patterns.
    # The probability variable p is uniquely determined per bit, so it does not change the count.
    # Explicit per-version branches so an undeclared future model_version fails loudly.
    name = op.__class__.__name__
    bitsize = op.input_vars[0].bitsize
    if op.model_version == f"{name}_XORDIFF":
        return 7 ** bitsize                        # per bit: out <= (in0 | in1)               -> 7
    elif op.model_version == f"{name}_LINEAR":
        return 5 ** bitsize                        # per bit: in0 <= out and in1 <= out        -> 5
    elif op.model_version == f"{name}_INTEGRAL_TWOSUBSET":
        return 4 ** bitsize                        # per bit: out == (in0 | in1)               -> 4
    else:
        raise AssertionError(f"unhandled model_version {op.model_version}")


def print_solutions(op, sol_list):
    # Print each solution as [in0,in1] -> [out] at the bit level.
    a = op.get_var_model("in", 0)
    b = op.get_var_model("in", 1)
    c = op.get_var_model("out", 0)
    for sol in sol_list:
        ins = ",".join("".join(str(round(float(sol[x])) ) for x in grp) for grp in (a, b))
        outs = "".join(str(round(float(sol[x]))) for x in c)
        log(f"  [{ins}] -> [{outs}]")


def check_solutions(op, sol_list):
    # Validity is characterized on (in0,in1,out) bit by bit; the weight variable p is auxiliary.
    name = op.__class__.__name__
    a = op.get_var_model("in", 0)
    b = op.get_var_model("in", 1)
    c = op.get_var_model("out", 0)
    for sol in sol_list:
        av = [round(float(sol[x])) for x in a]  # normalize MILP float/-0.0 & SAT int
        bv = [round(float(sol[x])) for x in b]
        cv = [round(float(sol[x])) for x in c]
        for i in range(len(cv)):
            if op.model_version == f"{name}_XORDIFF":
                assert cv[i] <= (av[i] | bv[i]), f"XORDIFF: out active requires in0|in1 at bit {i} in {sol}"
            elif op.model_version == f"{name}_LINEAR":
                assert av[i] <= cv[i] and bv[i] <= cv[i], f"LINEAR: in0,in1 must imply out at bit {i} in {sol}"
            elif op.model_version == f"{name}_INTEGRAL_TWOSUBSET":
                assert cv[i] == (av[i] | bv[i]), f"INTEGRAL_TWOSUBSET: out != in0|in1 at bit {i} in {sol}"
            else:
                raise AssertionError(f"unhandled model_version {op.model_version}")


def gen_operator(bitsize=2):
    log("\n********************* operation: AND ********************* ")
    my_input = [var.Variable(bitsize, ID="in" + str(i)) for i in range(2)]
    my_output = [var.Variable(bitsize, ID="out")]
    op = AND(my_input, my_output, ID='AND')
    op.display()
    return op


def test_implementation(op):
    code = op.generate_implementation(implementation_type="python", unroll=True)
    log(f"python code with unroll=True: \n", "\n".join(code))
    assert code == ["out = in0 & in1"], f"python implementation: {code}"

    code = op.generate_implementation(implementation_type="c", unroll=True)
    log(f"c code with unroll=True: \n", "\n".join(code))
    assert code == ["out = in0 & in1;"], f"c implementation: {code}"

    code = op.generate_implementation(implementation_type="verilog", unroll=True)
    log(f"verilog code with unroll=True: \n", "\n".join(code))
    assert code == ["assign out = in0 & in1;"], f"verilog implementation: {code}"


def test_milp_model(op):
    model_versions = [op.__class__.__name__ + "_" + v for v in ("XORDIFF", "LINEAR", "INTEGRAL_TWOSUBSET")]
    for model_v in model_versions:
        op.model_version = model_v
        milp_constraints = op.generate_model(model_type='milp')
        log(f"MILP constraints with model_version={model_v}: \n", "\n".join(milp_constraints))
        filename = str(FILES_DIR / f"milp_{op.ID}_{model_v}.lp")
        model = milp_search.write_milp_model(constraints=milp_constraints, filename=filename)
        sol_list = solving.solve_milp(filename, {"solution_number": 100000})
        log(f"Number of solutions: {len(sol_list)}")
        print_solutions(op, sol_list)
        expected = expected_solution_count(op)
        assert len(sol_list) == expected, f"{model_v}: MILP has {len(sol_list)} solutions, expected {expected}"
        check_solutions(op, sol_list)


def test_sat_model(op):
    model_versions = [op.__class__.__name__ + "_" + v for v in ("XORDIFF", "LINEAR")]
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
        expected = expected_solution_count(op)
        assert len(sol_list) == expected, f"{model_v}: SAT has {len(sol_list)} solutions, expected {expected}"
        check_solutions(op, sol_list)


def test_and(bitsize):

    op = gen_operator(bitsize=bitsize)

    test_implementation(op)

    test_milp_model(op)

    test_sat_model(op)


if __name__ == '__main__':
    log_path = FILES_DIR / "test_and_log.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log("=== Implementation Test Log ===")

        test_and(bitsize=1)
        test_and(bitsize=2)
        test_and(bitsize=3)
        test_and(bitsize=4)

        log("All implementation tests completed!")

    print(f"log written to {log_path}")
