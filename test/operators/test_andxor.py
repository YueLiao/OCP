import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # this file -> test -> <ROOT>
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import variables.variables as var
from operators.boolean_operators import ANDXOR
import tools.milp_search as milp_search
import tools.sat_search as sat_search
import solving.solving as solving

FILES_DIR = ROOT / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

_LOG = sys.stdout

# Static difference/linear tables of the 3-bit map out = (in0 & in1) ^ in2, used as the
# ground-truth validity oracle for check_solutions (index = (in0<<2)|(in1<<1)|in2).
_DDT = ANDXOR.bit_andxor_ddt()  # _DDT[din][dout] = #{x : F(x)^F(x^din) = dout}
_LAT = ANDXOR.bit_andxor_lat()  # _LAT[a][b]      = correlation of input mask a, output mask b


def log(*args):
    print(*args, file=_LOG)


def expected_solution_count(op):
    # ANDXOR is nonlinear; each bit contributes a fixed number of valid patterns (including the
    # uniquely-determined weight variable p). XORDIFF_1 / LINEAR_1 are alternative MILP encodings
    # of the same valid set, so they share the counts of XORDIFF / LINEAR.
    name = op.__class__.__name__
    bitsize = op.input_vars[0].bitsize
    if op.model_version in (f"{name}_XORDIFF", f"{name}_XORDIFF_1"):
        return 14 ** bitsize                       # per bit: valid differential propagations (DDT>0)
    elif op.model_version in (f"{name}_LINEAR", f"{name}_LINEAR_1"):
        return 5 ** bitsize                        # per bit: valid linear approximations (LAT!=0)
    else:
        raise AssertionError(f"unhandled model_version {op.model_version}")


def print_solutions(op, sol_list):
    # Print each solution as [in0,in1,in2] -> [out] at the bit level.
    groups = [op.get_var_model("in", i) for i in range(3)]
    c = op.get_var_model("out", 0)
    for sol in sol_list:
        ins = ",".join("".join(str(round(float(sol[x]))) for x in grp) for grp in groups)
        outs = "".join(str(round(float(sol[x]))) for x in c)
        log(f"  [{ins}] -> [{outs}]")


def check_solutions(op, sol_list):
    # Each solution must be a valid differential (DDT>0) or linear (LAT!=0) propagation per bit.
    name = op.__class__.__name__
    g0 = op.get_var_model("in", 0)
    g1 = op.get_var_model("in", 1)
    g2 = op.get_var_model("in", 2)
    c = op.get_var_model("out", 0)
    for sol in sol_list:
        v0 = [round(float(sol[x])) for x in g0]  # normalize MILP float/-0.0 & SAT int
        v1 = [round(float(sol[x])) for x in g1]
        v2 = [round(float(sol[x])) for x in g2]
        cv = [round(float(sol[x])) for x in c]
        for i in range(len(cv)):
            idx = (v0[i] << 2) | (v1[i] << 1) | v2[i]
            if op.model_version in (f"{name}_XORDIFF", f"{name}_XORDIFF_1"):
                assert _DDT[idx][cv[i]] > 0, f"{op.model_version}: invalid differential (DDT=0) at bit {i} in {sol}"
            elif op.model_version in (f"{name}_LINEAR", f"{name}_LINEAR_1"):
                assert _LAT[idx][cv[i]] != 0, f"{op.model_version}: invalid linear approx (LAT=0) at bit {i} in {sol}"
            else:
                raise AssertionError(f"unhandled model_version {op.model_version}")


def gen_operator(bitsize=2):
    log("\n********************* operation: ANDXOR ********************* ")
    my_input = [var.Variable(bitsize, ID="in" + str(i)) for i in range(3)]
    my_output = [var.Variable(bitsize, ID="out")]
    op = ANDXOR(my_input, my_output, ID='ANDXOR')
    op.display()
    return op


def test_implementation(op):
    code = op.generate_implementation(implementation_type="python", unroll=True)
    log(f"python code with unroll=True: \n", "\n".join(code))
    assert code == ["out = (in0 & in1) ^ in2"], f"python implementation: {code}"

    code = op.generate_implementation(implementation_type="c", unroll=True)
    log(f"c code with unroll=True: \n", "\n".join(code))
    assert code == ["out = (in0 & in1) ^ in2;"], f"c implementation: {code}"

    code = op.generate_implementation(implementation_type="verilog", unroll=True)
    log(f"verilog code with unroll=True: \n", "\n".join(code))
    assert code == ["assign out = (in0 & in1) ^ in2;"], f"verilog implementation: {code}"


def test_milp_model(op):
    model_versions = [op.__class__.__name__ + "_" + v for v in ("XORDIFF", "XORDIFF_1", "LINEAR", "LINEAR_1")]
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


def test_andxor(bitsize):

    op = gen_operator(bitsize=bitsize)

    test_implementation(op)

    test_milp_model(op)

    test_sat_model(op)


if __name__ == '__main__':
    log_path = FILES_DIR / "test_andxor_log.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log("=== Implementation Test Log ===")

        test_andxor(bitsize=1)
        test_andxor(bitsize=2)
        test_andxor(bitsize=3)
        test_andxor(bitsize=4)

        log("All implementation tests completed!")

    print(f"log written to {log_path}")
