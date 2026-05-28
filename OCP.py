"""
This module provides usage examples for the SPECK primitive and SPECK block cipher, including:

1. Generating software implementations and visualizations
2. Conducting differential cryptanalysis using MILP and SAT methods

Note:
For examples of other ciphers, refer to the following folders:
- test/implementation
- test/differential_cryptanalysis
"""

from pathlib import Path

from kiwisolver import Variable
import implementations.implementations as imp
import visualisations.visualisations as vis
import attacks.attacks as attacks
from tools.paths import get_files_dir

FILES_DIR = get_files_dir()

# ********************* IMPLEMENTATIONS ********************* #
def _test_generated_implementation(cipher, language, extension, tester, unroll=False):
    suffix = "_unrolled" if unroll else ""
    output_path = FILES_DIR / f"{cipher.name}{suffix}.{extension}"
    imp.generate_implementation(cipher, output_path, language, unroll)
    if cipher.test_vectors == []:
        print("warning: no test vector defined!")
        return False
    implementation_name = cipher.name + suffix
    for tv in cipher.test_vectors:
        tester(cipher, implementation_name, tv[0], tv[1])
    return True


def test_python_imp(cipher): # Generate Python implementation and test it with the test vectors
    return _test_generated_implementation(cipher, "python", "py", imp.test_implementation_python)

def test_python_unrolled_imp(cipher): # Generate unrolled Python implementation and test it with the test vectors
    return _test_generated_implementation(cipher, "python", "py", imp.test_implementation_python, unroll=True)

def test_c_imp(cipher): # Generate C implementation and test it with the test vectors
    return _test_generated_implementation(cipher, "c", "c", imp.test_implementation_c)

def test_c_unrolled_imp(cipher): # Generate unrolled C implementation and test it with the test vectors
    return _test_generated_implementation(cipher, "c", "c", imp.test_implementation_c, unroll=True)

def test_verilog_imp(cipher): # Generate Verilog implementation and test it with the test vectors
    return _test_generated_implementation(cipher, "verilog", "sv", imp.test_implementation_verilog)

def test_verilog_unrolled_imp(cipher): # Generate unrolled Verilog implementation and test it with the test vectors
    return _test_generated_implementation(cipher, "verilog", "sv", imp.test_implementation_verilog, unroll=True)

def test_all_implementations(cipher): # Generate all implementations
    #test_python_imp(cipher)
    test_python_unrolled_imp(cipher)
    #test_c_imp(cipher)
    test_c_unrolled_imp(cipher)
    #test_verilog_imp(cipher)
    #test_verilog_unrolled_imp(cipher)


# ********************* VISUALIZATIONS ********************* #
def test_visualisation(cipher): # Generate visualisation figure
    vis.generate_figure(cipher, FILES_DIR / f"{cipher.name}.pdf")

# ********************* Differential Cryptanalysis ********************* #
def test_diff_attack_milp(cipher):
    # Example: default parameters. Refer to test/differential_cryptanalysis/ for more available parameters.
    goal="DIFFERENTIALPATH_PROB"
    constraints=["INPUT_NOT_ZERO"]
    objective_target="OPTIMAL"
    show_mode=0
    config_model=None
    config_solver=None

    # Search for the differential trail
    trails = attacks.diff_attacks(cipher, goal=goal, constraints=constraints, objective_target=objective_target, show_mode=show_mode, config_model=config_model, config_solver=config_solver)

def test_diff_attack_sat(cipher):
    # Example: default parameters. Refer to test/differential_cryptanalysis/ for more available parameters.
    goal="DIFFERENTIALPATH_PROB"
    constraints=["INPUT_NOT_ZERO"]
    objective_target="OPTIMAL"
    show_mode=0
    config_model={"model_type": "sat"}
    config_solver=None

    # Search for the differential trail
    trails = attacks.diff_attacks(cipher, goal=goal, constraints=constraints, objective_target=objective_target, show_mode=show_mode, config_model=config_model, config_solver=config_solver)


# ********************* Linear Cryptanalysis ********************* #
def test_linear_attack_milp(cipher):
    # Example: default parameters. Refer to test/linear_cryptanalysis/ for more available parameters.
    goal="LINEARPATH_CORR"
    constraints=["INPUT_NOT_ZERO"]
    objective_target="OPTIMAL"
    show_mode=0
    config_model=None
    config_solver=None

    # Search for the linear trail
    trails = attacks.linear_attacks(cipher, goal=goal, constraints=constraints, objective_target=objective_target, show_mode=show_mode, config_model=config_model, config_solver=config_solver)

def test_linear_attack_sat(cipher):
    # Example: default parameters. Refer to test/linear_cryptanalysis/ for more available parameters.
    goal="LINEARPATH_CORR"
    constraints=["INPUT_NOT_ZERO"]
    objective_target="OPTIMAL"
    show_mode=0
    config_model={"model_type": "sat"}
    config_solver=None

    # Search for the linear trail
    trails = attacks.linear_attacks(cipher, goal=goal, constraints=constraints, objective_target=objective_target, show_mode=show_mode, config_model=config_model, config_solver=config_solver)


if __name__ == "__main__":
    # import primitives.aes as aes
    # cipher = aes.AES_BLOCKCIPHER(version=[128,256])

    # import primitives.speck as speck
    # cipher = speck.SPECK_PERMUTATION(version=32)
    # cipher = speck.SPECK_BLOCKCIPHER(version=[32,64])

    import primitives.simon as simon
    cipher = simon.SIMON_BLOCKCIPHER(version=[32,64])

    test_all_implementations(cipher)
    test_visualisation(cipher)
    test_diff_attack_milp(cipher)
    test_diff_attack_sat(cipher)
    test_linear_attack_milp(cipher)
    test_linear_attack_sat(cipher)
