import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # this file -> test -> <ROOT>
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import variables.variables as var
from operators.operators import CopyOperator
import tools.milp_search as milp_search
import tools.sat_search as sat_search
import solving.solving as solving

FILES_DIR = ROOT / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

_LOG = sys.stdout


def log(*args):
    print(*args, file=_LOG)

# Fixed at 2 outputs: every version then has both a MILP and a SAT path (the >=3-output
# word-nxor SAT path does not exist in the operator).
N_OUTPUTS = 2

# Prefix of every model_version string (e.g. "CopyOperator_XORDIFF").
CLS = CopyOperator.__name__


def expected_solution_count(model_version, bitsize, n_outputs):
    # Per-version solution counts, confirmed by solving. Explicit cases + else:raise so a new
    # version fails loudly rather than getting a wrong count.
    if model_version == f"{CLS}_XORDIFF":
        return 2 ** bitsize
    elif model_version == f"{CLS}_TRUNCATEDDIFF":
        return 2
    elif model_version == f"{CLS}_LINEAR":
        return 2 ** (bitsize * n_outputs)
    elif model_version == f"{CLS}_TRUNCATEDLINEAR":
        return 5  # word-XOR relaxation with exactly 2 outputs (independent of bitsize)
    elif model_version == f"{CLS}_INTEGRAL_TWOSUBSET":
        return (n_outputs + 1) ** bitsize
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
    # Assert Copy's per-version invariant on every solution. Values are MILP floats (incl -0.0) or
    # SAT ints; normalize with round(float(...)). Explicit cases + else:raise catch unhandled versions.
    v = op.model_version
    n = len(op.output_vars)

    def g(name, sol):
        return round(float(sol[name]))

    # copy-equivalence family: every output == input, bit (or word) for bit.
    if v in [f"{CLS}_XORDIFF", f"{CLS}_TRUNCATEDDIFF"]:
        bitwise = v == f"{CLS}_XORDIFF"
        var_in = op.get_var_model("in", 0, bitwise=bitwise)
        var_out = [op.get_var_model("out", j, bitwise=bitwise) for j in range(n)]
        for sol in sol_list:
            for j in range(n):
                for i in range(len(var_in)):
                    ov, iv = g(var_out[j][i], sol), g(var_in[i], sol)
                    assert ov == iv, f"{v}: {var_out[j][i]}={ov} != {var_in[i]}={iv} in {sol}"

    # linear/xor family: input relates to outputs by XOR. LINEAR holds strictly (bitwise XOR);
    # TRUNCATEDLINEAR is the word-XOR relaxation, so split inside the family.
    elif v in [f"{CLS}_LINEAR", f"{CLS}_TRUNCATEDLINEAR"]:
        if v == f"{CLS}_LINEAR":
            # Bitwise linear: input == XOR of outputs, bit for bit.
            var_in = op.get_var_model("in", 0, bitwise=True)
            var_out = [op.get_var_model("out", j, bitwise=True) for j in range(n)]
            for sol in sol_list:
                for i in range(len(var_in)):
                    x = 0
                    for j in range(n):
                        x ^= g(var_out[j][i], sol)
                    iv = g(var_in[i], sol)
                    assert iv == x, f"{v}: {var_in[i]}={iv} != XOR(outputs)={x} at bit {i} in {sol}"
        else:
            # Word-XOR relaxation: each active var must be supported by the others
            # (in<=out0+out1, out_j<=others+in). Strict XOR does NOT hold (out0=out1=in=1 is valid).
            var_in = op.get_var_model("in", 0, bitwise=False)
            var_out = [op.get_var_model("out", j, bitwise=False) for j in range(n)]
            for sol in sol_list:
                iv = g(var_in[0], sol)
                outs = [g(var_out[j][0], sol) for j in range(n)]
                assert iv <= sum(outs), f"{v}: in={iv} > sum(outs)={sum(outs)} in {sol}"
                for j in range(n):
                    others = sum(outs) - outs[j] + iv
                    assert outs[j] <= others, f"{v}: out{j}={outs[j]} unsupported (others+in={others}) in {sol}"

    # integral two-subset family: input bit = sum of output bits.
    elif v == f"{CLS}_INTEGRAL_TWOSUBSET":
        var_in = op.get_var_model("in", 0, bitwise=True)
        var_out = [op.get_var_model("out", j, bitwise=True) for j in range(n)]
        for sol in sol_list:
            for i in range(len(var_in)):
                s = sum(g(var_out[j][i], sol) for j in range(n))
                iv = g(var_in[i], sol)
                assert iv == s, f"{v}: {var_in[i]}={iv} != sum(outputs)={s} at bit {i} in {sol}"

    else:
        raise AssertionError(f"unhandled model_version {v}")


def gen_operator(bitsize=2, output_count=N_OUTPUTS):
    log("\n********************* operation: CopyOperator ********************* ")
    my_input = [var.Variable(bitsize, ID="in")]
    my_output = [var.Variable(bitsize, ID="out" + str(i)) for i in range(output_count)]
    op = CopyOperator(my_input, my_output, ID="Copy")
    op.display()
    return op


def test_implementation(op):
    n = len(op.output_vars)

    code = op.generate_implementation(implementation_type="python", unroll=True)
    log(f"python code with unroll=True: \n", "\n".join(code))
    assert code == [f"out{j} = in" for j in range(n)], f"python implementation: {code}"

    code = op.generate_implementation(implementation_type="c", unroll=True)
    log(f"c code with unroll=True: \n", "\n".join(code))
    assert code == [f"out{j} = in;" for j in range(n)], f"c implementation: {code}"

    code = op.generate_implementation(implementation_type="verilog", unroll=True)
    log(f"verilog code with unroll=True: \n", "\n".join(code))
    assert code == [f"assign out{j} = in;" for j in range(n)], f"verilog implementation: {code}"


def test_milp_model(op):
    # INTEGRAL_TWOSUBSET is milp-only, so it is tested here in the MILP loop (not in test_sat_model).
    model_versions = [op.__class__.__name__ + "_XORDIFF", op.__class__.__name__ + "_TRUNCATEDDIFF", op.__class__.__name__ + "_LINEAR", op.__class__.__name__ + "_TRUNCATEDLINEAR", op.__class__.__name__ + "_INTEGRAL_TWOSUBSET"]
    for model_v in model_versions:
        op.model_version = model_v
        milp_constraints = op.generate_model(model_type='milp')
        log(f"MILP constraints with model_version={model_v}: \n", "\n".join(milp_constraints))
        filename = str(FILES_DIR / f"milp_{op.ID}_{model_v}.lp")
        model = milp_search.write_milp_model(constraints=milp_constraints, filename=filename)
        sol_list = solving.solve_milp(filename, {"solution_number": 100000})
        log(f"Number of solutions: {len(sol_list)}")
        print_solutions(op, sol_list)
        expected = expected_solution_count(model_v, op.input_vars[0].bitsize, len(op.output_vars))
        assert len(sol_list) == expected, f"{model_v}: MILP has {len(sol_list)} solutions, expected {expected}"
        check_solutions(op, sol_list)


def test_sat_model(op):
    model_versions = [op.__class__.__name__ + "_XORDIFF", op.__class__.__name__ + "_TRUNCATEDDIFF", op.__class__.__name__ + "_LINEAR", op.__class__.__name__ + "_TRUNCATEDLINEAR"]
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
        expected = expected_solution_count(model_v, op.input_vars[0].bitsize, len(op.output_vars))
        assert len(sol_list) == expected, f"{model_v}: SAT has {len(sol_list)} solutions, expected {expected}"
        check_solutions(op, sol_list)


def test_copy(bitsize, output_count=N_OUTPUTS):

    op = gen_operator(bitsize=bitsize, output_count=output_count)

    test_implementation(op)

    test_milp_model(op)

    test_sat_model(op)


if __name__ == "__main__":
    log_path = FILES_DIR / "test_copy_log.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log("=== Implementation Test Log ===")

        test_copy(bitsize=1)

        test_copy(bitsize=2)

        test_copy(bitsize=3)

        test_copy(bitsize=4)

        log("All implementation tests completed!")
    print(f"log written to {log_path}")
