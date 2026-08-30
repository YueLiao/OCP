"""S-box operators in Sbox.py: DDT/LAT/truth tables, code generation (incl. bit-sliced),
per-class model caching, weight helpers, and bitwise operators represented as S-boxes.
"""
import shutil

import pytest

import variables.variables as var
from operators.Sbox import AES_Sbox, PRESENT_Sbox, RECTANGLE_Sbox, Sbox


def test_bitwise_or_as_sbox_has_stable_ddt_and_lat():
    op = Sbox(
        [var.Variable(2, ID="in")],
        [var.Variable(1, ID="out")],
        input_bitsize=2,
        output_bitsize=1,
        ID="or_sbox",
    )
    op.table = [0, 1, 1, 1]

    assert op.computeDDT() == [[4, 0], [2, 2], [2, 2], [2, 2]]
    assert op.computeLAT() == [[4, -2], [0, 2], [0, 2], [0, 2]]


def test_non_square_bitwise_sbox_implementation_uses_output_width():
    op = Sbox(
        [var.Variable(1, ID="a"), var.Variable(1, ID="b")],
        [var.Variable(1, ID="out")],
        input_bitsize=2,
        output_bitsize=1,
        ID="or_sbox",
    )
    op.table = [0, 1, 1, 1]

    assert op.generate_implementation("python", unroll=True) == [
        "x = (a << 1) | (b << 0)",
        "y = Sbox[x]",
        "out = (y >> 0) & 1",
    ]
    assert op.generate_implementation("c", unroll=True) == [
        "x = (a << 1) | (b << 0);",
        "y = Sbox[x];",
        "out = (y >> 0) & 1;",
    ]
    assert op.generate_implementation_header("c") == [
        "uint8_t Sbox[4] = {0, 1, 1, 1};",
        "uint8_t x;",
        "uint8_t y;",
    ]


def test_present_sbox_ddt_lat_and_truth_tables_are_stable():
    op = PRESENT_Sbox([var.Variable(4, ID="in")], [var.Variable(4, ID="out")], ID="S")

    assert op.computeDDT()[0] == [16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    assert op.computeDDT()[1] == [0, 0, 0, 4, 0, 0, 0, 4, 0, 4, 0, 0, 0, 4, 0, 0]
    assert op.computeLAT()[0] == [16, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    assert op.computeLAT()[1] == [0, 0, 0, 0, 0, -8, 0, -8, 0, 0, 0, 0, 0, -8, 0, 8]

    ddt_truth = op.star_ddt_to_truthtable()
    lat_truth = op.star_lat_to_truthtable()

    assert len(ddt_truth) == 256
    assert ddt_truth.count("1") == 97
    assert len(lat_truth) == 256
    assert lat_truth.count("1") == 133


def test_present_sbox_code_generation_and_branch_numbers_are_stable():
    op = PRESENT_Sbox([var.Variable(4, ID="in")], [var.Variable(4, ID="out")], ID="S")

    assert op.is_bijective()
    assert op.differential_branch_number() == 3
    assert op.linear_branch_number() == 2
    assert op.generate_implementation("python", unroll=True) == ["out = PRESENT_Sbox[in]"]
    assert op.generate_implementation("c", unroll=True) == ["out = PRESENT_Sbox[in];"]
    assert op.generate_implementation_header("python") == [
        "PRESENT_Sbox = [12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2]",
    ]
    assert op.generate_implementation_header("c") == [
        "uint8_t PRESENT_Sbox[16] = {12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2};",
    ]


def test_present_sbox_bitsliced_code_generation_is_stable():
    op = PRESENT_Sbox(
        [var.Variable(1, ID=f"in{i}") for i in range(4)],
        [var.Variable(1, ID=f"out{i}") for i in range(4)],
        ID="Sbits",
    )

    assert op.generate_implementation("python", unroll=True) == [
        "x = (in0 << 3) | (in1 << 2) | (in2 << 1) | (in3 << 0)",
        "y = PRESENT_Sbox[x]",
        "out0, out1, out2, out3 = (y >> 3) & 1, (y >> 2) & 1, (y >> 1) & 1, (y >> 0) & 1",
    ]
    assert op.generate_implementation("c", unroll=True) == [
        "x = (in0 << 3) | (in1 << 2) | (in2 << 1) | (in3 << 0);",
        "y = PRESENT_Sbox[x];",
        "out0 = (y >> 3) & 1;",
        "out1 = (y >> 2) & 1;",
        "out2 = (y >> 1) & 1;",
        "out3 = (y >> 0) & 1;",
    ]
    assert op.generate_implementation_header("c") == [
        "uint8_t PRESENT_Sbox[16] = {12, 5, 6, 11, 9, 0, 10, 13, 3, 14, 15, 8, 4, 7, 1, 2};",
        "uint8_t x;",
        "uint8_t y;",
    ]


def test_sbox_implementation_validation_errors_are_readable():
    op = PRESENT_Sbox([], [var.Variable(4, ID="out")], ID="S")

    with pytest.raises(ValueError, match="unsupported number of input/output variables"):
        op.generate_implementation("python", unroll=True)

    with pytest.raises(ValueError, match="unknown implementation type 'rust'"):
        op.generate_implementation("rust", unroll=True)


@pytest.mark.skipif(shutil.which("espresso") is None, reason="espresso CLI not on PATH")
def test_sbox_model_cache_paths_are_per_named_class(monkeypatch, tmp_path):
    monkeypatch.setenv("OCP_FILES_DIR", str(tmp_path))

    present = PRESENT_Sbox([var.Variable(4, ID="x")], [var.Variable(4, ID="y")], ID="S")
    rectangle = RECTANGLE_Sbox([var.Variable(4, ID="x")], [var.Variable(4, ID="y")], ID="S")
    present.model_version = "PRESENT_Sbox_XORDIFF"
    rectangle.model_version = "RECTANGLE_Sbox_XORDIFF"

    present.generate_model("sat", filename_load=False)
    rectangle.generate_model("sat", filename_load=False)

    # Distinct named S-boxes -> distinct template files (the class name is carried in model_version);
    # the path honours OCP_FILES_DIR and follows constraints_<type>_<version>_<tool>_<mode>.txt.
    assert present.model_filename != rectangle.model_filename
    assert present.model_filename.startswith(str(tmp_path / "sbox_modeling"))
    assert present.model_filename.endswith("constraints_sat_PRESENT_Sbox_XORDIFF_minimize_logic_0.txt")


def test_present_sbox_weighted_truth_tables_are_stable():
    op = PRESENT_Sbox([var.Variable(4, ID="in")], [var.Variable(4, ID="out")], ID="S")

    expected = {
        "ddt_to_truthtable_milp": (1024, 97, "10000000000000000000000000000000", "00000000000000000000000001000100"),
        "ddt_to_truthtable_sat": (2048, 97, "10000000000000000000000000000000", "00000000000000000001000000010000"),
        "lat_to_truthtable_milp": (1024, 133, "10000000000000000000000000000000", "00100010010000000010001000000000"),
        "lat_to_truthtable_sat": (1024, 133, "10000000000000000000000000000000", "00010001010000000001000100000000"),
    }

    for method_name, (length, active_count, prefix, suffix) in expected.items():
        truth_table = getattr(op, method_name)()
        assert len(truth_table) == length
        assert truth_table.count("1") == active_count
        assert truth_table[:32] == prefix
        assert truth_table[-32:] == suffix


def test_sbox_weight_helpers_and_aes_header_are_stable():
    present = PRESENT_Sbox([var.Variable(4, ID="in")], [var.Variable(4, ID="out")], ID="S")
    aes = AES_Sbox([var.Variable(8, ID="ain")], [var.Variable(8, ID="aout")], ID="AES")

    assert present.gen_weights(present.computeDDT()) == [3.0, 2.0]
    assert present.gen_integer_float_weight(present.computeLAT()) == ([1, 2], [])
    assert present.gen_weight_pattern_sat([1, 2], [0.5], 2.5) == [1, 1, 1]
    assert aes.is_bijective()
    assert aes.differential_branch_number() == 2
    assert aes.linear_branch_number() == 2
    assert aes.generate_implementation_header("c")[0].startswith(
        "uint8_t AES_Sbox[256] = {99, 124, 119, 123",
    )
