import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # this file -> test -> <ROOT>
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import variables.variables as var
from operators.operators import Equal
import tools.milp_search as milp_search
import tools.sat_search as sat_search
import solving.solving as solving

FILES_DIR = ROOT / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

_LOG = sys.stdout


def log(*args):
    print(*args, file=_LOG)


def expected_solution_count(op, bitsize):
    name = op.__class__.__name__
    if op.model_version in [f"{name}_XORDIFF", f"{name}_LINEAR", f"{name}_INTEGRAL_TWOSUBSET"]:
        return 2 ** bitsize          # bit-level: each bit free, out follows in
    elif op.model_version in [f"{name}_TRUNCATEDDIFF", f"{name}_TRUNCATEDLINEAR"]:
        return 2                     # word-level: the shared activity bit is 0 or 1
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
    # Every solution must satisfy Equal's invariant: input == output.
    name = op.__class__.__name__
    if op.model_version in [f"{name}_XORDIFF", f"{name}_LINEAR", f"{name}_INTEGRAL_TWOSUBSET"]:
        var_in, var_out = op.get_var_model("in", 0), op.get_var_model("out", 0)
    elif op.model_version in [f"{name}_TRUNCATEDDIFF", f"{name}_TRUNCATEDLINEAR"]:
        var_in, var_out = op.get_var_model("in", 0, bitwise=False), op.get_var_model("out", 0, bitwise=False)
    else:
        raise AssertionError(f"unhandled model_version {op.model_version}")
    for sol in sol_list:
        for vin, vout in zip(var_in, var_out):
            iv, ov = round(float(sol[vin])), round(float(sol[vout]))  # normalize MILP float/-0.0 & SAT int
            assert iv == ov, f"{op.model_version}: {vin}={iv} != {vout}={ov} in solution {sol}"


def gen_operator(bitsize=2):
    log("\n********************* operation: Equal ********************* ")
    my_input, my_output = [var.Variable(bitsize, ID="in")], [var.Variable(bitsize, ID="out")]
    op = Equal(my_input, my_output, ID='Equal')
    # op.display(output_func=log)
    return op


def test_implementation(op):
    code = op.generate_implementation(implementation_type="python", unroll=True)
    log(f"python code with unroll=True: \n", "\n".join(code))
    assert code == ["out = in"], f"python implementation: {code}"

    code = op.generate_implementation(implementation_type="c", unroll=True)
    log(f"c code with unroll=True: \n", "\n".join(code))
    assert code == ["out = in;"], f"c implementation: {code}"

    code = op.generate_implementation(implementation_type="verilog", unroll=True)
    log(f"verilog code with unroll=True: \n", "\n".join(code))
    assert code == ["assign out = in;"], f"verilog implementation: {code}"


def test_milp_model(op):
    model_versions = [op.__class__.__name__+"_XORDIFF", op.__class__.__name__+"_TRUNCATEDDIFF", op.__class__.__name__+"_LINEAR", op.__class__.__name__+"_TRUNCATEDLINEAR"]
    for model_v in model_versions:
        op.model_version = model_v
        milp_constraints = op.generate_model(model_type='milp')
        log(f"MILP constraints with model_version={model_v}: \n", "\n".join(milp_constraints))
        filename = str(FILES_DIR / f"milp_{op.ID}_{model_v}.lp")
        model = milp_search.write_milp_model(constraints=milp_constraints, filename=filename)
        sol_list = solving.solve_milp(filename, {"solution_number": 100000})
        log(f"Number of solutions: {len(sol_list)}")
        print_solutions(op, sol_list)
        expected = expected_solution_count(op, op.input_vars[0].bitsize)
        assert len(sol_list) == expected, f"{model_v}: MILP has {len(sol_list)} solutions, expected {expected}"
        check_solutions(op, sol_list)


def test_sat_model(op):
    model_versions = [op.__class__.__name__+"_XORDIFF", op.__class__.__name__+"_TRUNCATEDDIFF", op.__class__.__name__+"_LINEAR", op.__class__.__name__+"_TRUNCATEDLINEAR"]
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
        expected = expected_solution_count(op, op.input_vars[0].bitsize)
        assert len(sol_list) == expected, f"{model_v}: SAT has {len(sol_list)} solutions, expected {expected}"
        check_solutions(op, sol_list)

def test_equal_twosubset(op):
    op.model_version = op.__class__.__name__ + "_INTEGRAL_TWOSUBSET"
    milp_constraints = op.generate_model(model_type='milp')
    log(f"MILP constraints with model_version={op.model_version}: \n", "\n".join(milp_constraints))
    filename = str(FILES_DIR / f"milp_{op.ID}_{op.model_version}.lp")
    milp_search.write_milp_model(constraints=milp_constraints, filename=filename)
    sol_list = solving.solve_milp(filename, {"solution_number": 100000})
    log(f"Number of solutions: {len(sol_list)}")
    print_solutions(op, sol_list)
    expected = expected_solution_count(op, op.input_vars[0].bitsize)
    assert len(sol_list) == expected, f"{op.model_version}: MILP has {len(sol_list)} solutions, expected {expected}"
    check_solutions(op, sol_list)

    # INTEGRAL_TWOSUBSET is MILP only: SAT must be rejected.
    try:
        op.generate_model(model_type='sat')
    except Exception as exc:
        assert "not existing for sat" in str(exc)
    else:
        raise AssertionError("Equal_INTEGRAL_TWOSUBSET must reject non-MILP model_type")


def test_equal(bitsize):

    op = gen_operator(bitsize=bitsize)

    test_implementation(op)

    test_equal_twosubset(op)

    test_milp_model(op)

    test_sat_model(op)


if __name__ == '__main__':
    log_path = FILES_DIR / "test_equal_log.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log(f"=== Implementation Test Log ===")

        test_equal(bitsize=1)

        test_equal(bitsize=2)

        test_equal(bitsize=3)

        test_equal(bitsize=4)

        log("All implementation tests completed!")

    print(f"log written to {log_path}")
