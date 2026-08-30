import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # this file -> test -> <ROOT>
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import variables.variables as var
from operators.boolean_operators import XOR
import tools.milp_search as milp_search
import tools.sat_search as sat_search
import solving.solving as solving

FILES_DIR = ROOT / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

_LOG = sys.stdout


def log(*args):
    print(*args, file=_LOG)


def expected_solution_count(op):
    # XOR is linear, so the number of valid patterns is exact and independent of the direction.
    # Explicit per-version branches so an undeclared future model_version fails loudly.
    name = op.__class__.__name__
    bitsize = op.input_vars[0].bitsize
    if op.model_version == f"{name}_XORDIFF":
        return 2 ** (2 * bitsize)                 # per bit: in0,in1 free, out = in0^in1  -> 4 per bit
    elif op.model_version == f"{name}_LINEAR":
        return 2 ** bitsize                        # per bit: all three masks equal      -> 2 per bit
    elif op.model_version == f"{name}_TRUNCATEDDIFF":
        return 5                                   # word activity: any pattern except exactly one active
    elif op.model_version == f"{name}_TRUNCATEDLINEAR":
        return 2                                   # word activity: all three equal      -> (0,0,0),(1,1,1)
    else:
        raise AssertionError(f"unhandled model_version {op.model_version}")


def print_solutions(op, sol_list):
    # Print each solution as [in0,in1] -> [out] (bit-level or word-level to match the model_version).
    bitwise = "TRUNCATED" not in op.model_version
    for sol in sol_list:
        ins = ",".join("".join(str(round(float(sol[b]))) for b in op.get_var_model("in", i, bitwise=bitwise))
                       for i in range(len(op.input_vars)))
        outs = ",".join("".join(str(round(float(sol[b]))) for b in op.get_var_model("out", i, bitwise=bitwise))
                        for i in range(len(op.output_vars)))
        log(f"  [{ins}] -> [{outs}]")


def check_solutions(op, sol_list):
    # Each solution must satisfy the XOR relation for its model_version.
    # Explicit per-version branches so an undeclared future model_version fails loudly.
    name = op.__class__.__name__
    bitwise = "TRUNCATED" not in op.model_version
    a = op.get_var_model("in", 0, bitwise=bitwise)
    b = op.get_var_model("in", 1, bitwise=bitwise)
    c = op.get_var_model("out", 0, bitwise=bitwise)

    for sol in sol_list:
        av = [round(float(sol[x])) for x in a]  # normalize MILP float/-0.0 & SAT int
        bv = [round(float(sol[x])) for x in b]
        cv = [round(float(sol[x])) for x in c]
        if op.model_version == f"{name}_XORDIFF":
            for i in range(len(cv)):
                assert cv[i] == (av[i] ^ bv[i]), f"XORDIFF: out != in0^in1 at bit {i} in {sol}"
        elif op.model_version == f"{name}_LINEAR":
            for i in range(len(cv)):
                assert av[i] == bv[i] == cv[i], f"LINEAR: masks must be equal at bit {i} in {sol}"
        elif op.model_version == f"{name}_TRUNCATEDDIFF":
            assert (av[0] + bv[0] + cv[0]) != 1, f"TRUNCATEDDIFF: 'exactly one active' is invalid in {sol}"
        elif op.model_version == f"{name}_TRUNCATEDLINEAR":
            assert av[0] == bv[0] == cv[0], f"TRUNCATEDLINEAR: activities must be equal in {sol}"
        else:
            raise AssertionError(f"unhandled model_version {op.model_version}")


def gen_operator(bitsize=2):
    log("\n********************* operation: XOR ********************* ")
    my_input = [var.Variable(bitsize, ID="in" + str(i)) for i in range(2)]
    my_output = [var.Variable(bitsize, ID="out")]
    op = XOR(my_input, my_output, ID='XOR')
    op.display()
    return op


def test_implementation(op):
    code = op.generate_implementation(implementation_type="python", unroll=True)
    log(f"python code with unroll=True: \n", "\n".join(code))
    assert code == ["out = in0 ^ in1"], f"python implementation: {code}"

    code = op.generate_implementation(implementation_type="c", unroll=True)
    log(f"c code with unroll=True: \n", "\n".join(code))
    assert code == ["out = in0 ^ in1;"], f"c implementation: {code}"

    code = op.generate_implementation(implementation_type="verilog", unroll=True)
    log(f"verilog code with unroll=True: \n", "\n".join(code))
    assert code == ["assign out = in0 ^ in1;"], f"verilog implementation: {code}"


def test_milp_model(op):
    model_versions = [op.__class__.__name__ + "_" + v for v in ("XORDIFF", "LINEAR", "TRUNCATEDDIFF", "TRUNCATEDLINEAR")]
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
    model_versions = [op.__class__.__name__ + "_" + v for v in ("XORDIFF", "LINEAR", "TRUNCATEDDIFF", "TRUNCATEDLINEAR")]
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


def test_xor(bitsize):

    op = gen_operator(bitsize=bitsize)

    test_implementation(op)

    test_milp_model(op)

    test_sat_model(op)


if __name__ == '__main__':
    log_path = FILES_DIR / "test_xor_log_new.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log("=== Implementation Test Log ===")

        test_xor(bitsize=1)
        test_xor(bitsize=2)
        test_xor(bitsize=3)
        test_xor(bitsize=4)

        log("All implementation tests completed!")

    print(f"log written to {log_path}")
