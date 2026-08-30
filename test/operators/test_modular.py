import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # this file -> test -> <ROOT>
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import variables.variables as var
from operators.modular_operators import ModAdd
import tools.milp_search as milp_search
import tools.sat_search as sat_search
import solving.solving as solving

FILES_DIR = ROOT / "files"
FILES_DIR.mkdir(parents=True, exist_ok=True)

_LOG = sys.stdout


def log(*args):
    print(*args, file=_LOG)


# ---------------------------------------------------------------------------
# Independent references.
#
# Bit order convention (verified empirically against the models): the model
# variables returned by get_var_model have index 0 = MSB, index n-1 = LSB, so a
# solution's bit list maps to an integer with weight 2^(n-1-i) at index i.
#
# ModAdd computes c = (a + b) mod 2^n.
#  * XORDIFF (and its _1/_2/_3 MILP variants): the feasible (alpha, beta, gamma)
#    XOR-differentials are exactly those with non-zero probability -> brute-force DDT support.
#  * LINEAR: the feasible (mu, nu, omega) masks are those with non-zero correlation -> LAT support.
#  * INTEGRAL_TWOSUBSET: the Sun et al. model realises the bit-based (circuit-level) two-subset
#    division property, which is coarser than the exact ANF division property, so it is checked by
#    invariants + a pinned distinct-trail count rather than an ANF oracle. n=1 (ModAdd == bitwise
#    XOR) is pinned to its exact trail set.
# ---------------------------------------------------------------------------

def _to_int(bits):
    """Map a get_var_model bit list (index 0 = MSB) to an integer."""
    n = len(bits)
    return sum(bits[i] << (n - 1 - i) for i in range(n))


def modadd_ddt_support(n):
    """All XOR-differentials (alpha, beta, gamma) of c = (a + b) mod 2^n with non-zero probability."""
    M = 1 << n
    mask = M - 1
    support = set()
    for alpha in range(M):
        for beta in range(M):
            for gamma in range(M):
                for a in range(M):
                    for b in range(M):
                        if ((((a ^ alpha) + (b ^ beta)) & mask) ^ ((a + b) & mask)) == gamma:
                            support.add((alpha, beta, gamma))
                            break
                    else:
                        continue
                    break
    return support


def modadd_lat_support(n):
    """All linear masks (mu, nu, omega) of c = (a + b) mod 2^n with non-zero correlation."""
    M = 1 << n
    mask = M - 1
    parity = lambda x: bin(x).count("1") & 1
    support = set()
    for mu in range(M):
        for nu in range(M):
            for omega in range(M):
                corr = 0
                for a in range(M):
                    for b in range(M):
                        corr += 1 if parity((mu & a) ^ (nu & b) ^ (omega & ((a + b) & mask))) == 0 else -1
                if corr != 0:
                    support.add((mu, nu, omega))
    return support


# Distinct two-subset division trails the INTEGRAL_TWOSUBSET model must enumerate, per bitsize.
# n == 1 is exact (ModAdd == XOR); n >= 2 are regression pins of the circuit-level model (no exact
# ANF oracle applies). Bitsizes absent here skip the count check but still verify the invariants.
INTEGRAL_TRAIL_COUNT = {1: 3, 2: 13, 3: 75}
# n == 1: ModAdd degenerates to bitwise XOR, whose two-subset division trails are exact and known.
INTEGRAL_TRAILS_N1 = {(0, 0, 0), (0, 1, 1), (1, 0, 1)}


def gen_operator(bitsize):
    log(f"\n********************* operation: ModAdd (bitsize={bitsize}) ********************* ")
    my_input = [var.Variable(bitsize, ID="in" + str(i)) for i in range(2)]
    my_output = [var.Variable(bitsize, ID="out" + str(i)) for i in range(1)]
    op = ModAdd(my_input, my_output, ID="ModAdd")
    op.display()
    return op


def _solution_triple(op, sol):
    """Extract (alpha/mu, beta/nu, gamma/omega) integers from one solution."""
    a = _to_int([round(float(sol[b])) for b in op.get_var_model("in", 0)])
    b = _to_int([round(float(sol[b])) for b in op.get_var_model("in", 1)])
    c = _to_int([round(float(sol[b])) for b in op.get_var_model("out", 0)])
    return (a, b, c)


def check_solutions(op, model_version, sol_list):
    """Verify the input/output projection of the solutions against the model's ground truth."""
    n = op.input_vars[0].bitsize
    triples = {_solution_triple(op, s) for s in sol_list}   # dedup auxiliary-variable multiplicity

    if "INTEGRAL" in model_version:
        assert triples, f"{model_version}: no solutions"
        # Zero input division property propagates only to the zero output.
        zero_in = {t for t in triples if t[0] == 0 and t[1] == 0}
        assert zero_in == {(0, 0, 0)}, f"{model_version}: zero input must map to zero output only, got {zero_in}"
        if n in INTEGRAL_TRAIL_COUNT:
            assert len(triples) == INTEGRAL_TRAIL_COUNT[n], \
                f"{model_version}: {len(triples)} distinct trails, expected {INTEGRAL_TRAIL_COUNT[n]}"
        if n == 1:
            assert triples == INTEGRAL_TRAILS_N1, f"{model_version}: trails {triples} != {INTEGRAL_TRAILS_N1}"
    elif "LINEAR" in model_version:
        expected = modadd_lat_support(n)
        assert triples == expected, f"{model_version}: linear masks != LAT support"
    else:  # XORDIFF and the _1/_2/_3 MILP variants share one differential support
        expected = modadd_ddt_support(n)
        assert triples == expected, f"{model_version}: differentials != DDT support"


def test_implementation(op):
    n = op.input_vars[0].bitsize
    mask = hex(2 ** n - 1)
    code = op.generate_implementation(implementation_type="python", unroll=True)
    log("python code with unroll=True:\n", "\n".join(code))
    assert code == [f"out0 = (in0 + in1) & {mask}"], code

    code = op.generate_implementation(implementation_type="c", unroll=True)
    log("c code with unroll=True:\n", "\n".join(code))
    assert code == [f"out0 = (in0 + in1) & {mask};"], code


def test_milp_model(op):
    name = op.__class__.__name__
    model_versions = [name + "_XORDIFF", name + "_XORDIFF_1", name + "_XORDIFF_2",
                      name + "_XORDIFF_3", name + "_LINEAR", name + "_INTEGRAL_TWOSUBSET"]
    for model_version in model_versions:
        op.model_version = model_version
        milp_constraints = op.generate_model(model_type='milp')
        log(f"MILP constraints with model_version={model_version}:\n", "\n".join(milp_constraints))
        filename = str(FILES_DIR / f"milp_{op.ID}_{model_version}.lp")
        milp_search.write_milp_model(constraints=milp_constraints, obj_fun=op.weight, filename=filename)
        sol_list = solving.solve_milp(filename, {"solution_number": 100000})
        log(f"Number of solutions: {len(sol_list)}")
        check_solutions(op, model_version, sol_list)


def test_sat_model(op):
    name = op.__class__.__name__
    model_versions = [name + "_XORDIFF", name + "_LINEAR"]
    for model_version in model_versions:
        op.model_version = model_version
        sat_constraints = op.generate_model(model_type='sat')
        log(f"SAT constraints with model_version={model_version}:\n", "\n".join(sat_constraints))
        filename = str(FILES_DIR / f"sat_{op.ID}_{model_version}.cnf")
        model = sat_search.write_sat_model(constraints=sat_constraints, filename=filename)
        sol_list = solving.solve_sat(filename, model["variable_map"], {"solution_number": 100000})
        log(f"Number of solutions: {len(sol_list)}")
        check_solutions(op, model_version, sol_list)


def test_modadd(bitsize):

    op = gen_operator(bitsize=bitsize)

    test_implementation(op)

    test_milp_model(op)

    test_sat_model(op)


if __name__ == '__main__':
    log_path = FILES_DIR / "test_modadd_log.txt"
    with open(log_path, "w") as log_file:
        _LOG = log_file
        log("=== ModAdd operator test log ===")
        test_modadd(bitsize=1)
        test_modadd(bitsize=2)
        test_modadd(bitsize=3)
        log("All ModAdd tests passed!")
    print(f"log written to {log_path}")
