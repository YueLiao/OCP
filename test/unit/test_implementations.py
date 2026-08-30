"""Unit tests for the code-generation engine itself (implementations/implementations.py):
get_var_def_c, the compiler-availability probes, generate_implementation, evaluate_python,
and test_implementation_python - independent of any specific cipher's designer KAT. A tiny
SPECK-32 permutation is the fixture cipher (fast, ships a test vector).
"""
import io
from contextlib import redirect_stdout

import pytest

import implementations.implementations as imp
from tools.paths import DEFAULT_FILES_DIR, get_files_dir

from primitives.speck import SPECK_PERMUTATION


@pytest.fixture(autouse=True)
def _pin_files_dir(monkeypatch):
    # test_implementation_python resolves "files/<name>.py" relative to the CWD, while the
    # fixtures generate modules under get_files_dir(); pin both to the repo's default files/
    # dir so they agree regardless of the caller's CWD or a stray OCP_FILES_DIR.
    monkeypatch.delenv("OCP_FILES_DIR", raising=False)
    monkeypatch.chdir(DEFAULT_FILES_DIR.parent)


# ----------------------------- get_var_def_c: bit width -> C type -----------------------------
@pytest.mark.parametrize("bits,ctype", [
    (1, "uint8_t"), (8, "uint8_t"),
    (9, "uint32_t"), (32, "uint32_t"),
    (33, "uint64_t"), (64, "uint64_t"),
    (65, "uint128_t"), (128, "uint128_t"),
])
def test_get_var_def_c_picks_type_by_width(bits, ctype):
    assert imp.get_var_def_c(bits) == ctype


# ----------------------------- compiler availability probes -----------------------------
def test_is_c_compiler_available_reports_first_found(monkeypatch):
    monkeypatch.setattr(imp.shutil, "which", lambda name: "/usr/bin/gcc" if name == "gcc" else None)
    assert imp.is_c_compiler_available() == (True, "gcc")


def test_is_c_compiler_available_false_when_none_present(monkeypatch):
    monkeypatch.setattr(imp.shutil, "which", lambda name: None)
    assert imp.is_c_compiler_available() == (False, None)


def test_is_rust_compiler_available_is_boolean(monkeypatch):
    monkeypatch.setattr(imp.shutil, "which", lambda name: None)
    assert imp.is_rust_compiler_available() is False
    monkeypatch.setattr(imp.shutil, "which", lambda name: "/opt/rustc")
    assert imp.is_rust_compiler_available() is True


def test_is_verilog_compiler_available_reports_first_found(monkeypatch):
    monkeypatch.setattr(imp.shutil, "which", lambda name: "/usr/bin/iverilog" if name == "iverilog" else None)
    assert imp.is_verilog_compiler_available() == (True, "iverilog")
    monkeypatch.setattr(imp.shutil, "which", lambda name: None)
    assert imp.is_verilog_compiler_available() == (False, None)


# ----------------------------- generate_implementation -----------------------------
def test_generate_implementation_writes_named_function_and_creates_dirs(tmp_path):
    cipher = SPECK_PERMUTATION(r=None, version=32)
    out = tmp_path / "nested" / f"{cipher.name}.py"  # parent dir must be created by the engine
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(cipher, out, "python", True)
    assert out.exists()
    assert f"def {cipher.name}(" in out.read_text()


def test_generate_implementation_rolled_python_round_trips():
    # exercise the rolled (unroll=False) code path, which the KAT/gated suites never run
    cipher = SPECK_PERMUTATION(r=None, version=32)
    tv = cipher.test_vectors[0]
    cipher.name = "SPECK32ROLLED"  # distinct module so it doesn't clash with the unrolled fixture
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", False)
        got = imp.evaluate_python(cipher, tv[0], output_len=len(tv[1]))
    assert got == tv[1]


def test_generate_implementation_c_emits_named_function_and_typed_declarations(tmp_path):
    # the C emitter (string only, no compilation): SPECK-32 has 16-bit words, so get_var_def_c
    # maps them to uint32_t and the emitter must use that type in the signature.
    cipher = SPECK_PERMUTATION(r=None, version=32)
    out = tmp_path / f"{cipher.name}.c"
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(cipher, out, "c", True)
    text = out.read_text()
    assert "#include <stdint.h>" in text
    assert f"void {cipher.name}(" in text                          # named C function
    assert "uint32_t* IN_" in text and "uint32_t* OUT_" in text    # 16-bit words -> uint32_t


def test_generate_implementation_verilog_emits_named_module_and_logic_declarations(tmp_path):
    cipher = SPECK_PERMUTATION(r=None, version=32)
    out = tmp_path / f"{cipher.name}.sv"
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(cipher, out, "verilog", True)
    text = out.read_text()
    assert f"module {cipher.name}(" in text                        # named module
    assert "logic [" in text                                       # typed bit-vector declarations


# ----------------------------- evaluate_python (round-trips through the files/ package) -----------------------------
@pytest.fixture  # function-scoped so it runs after the autouse _pin_files_dir
def built_speck():
    cipher = SPECK_PERMUTATION(r=None, version=32)
    with redirect_stdout(io.StringIO()):
        imp.generate_implementation(cipher, get_files_dir() / f"{cipher.name}.py", "python", True)
    return cipher, cipher.test_vectors[0]


def test_evaluate_python_round_trips_vector(built_speck):
    cipher, tv = built_speck
    with redirect_stdout(io.StringIO()):
        got = imp.evaluate_python(cipher, tv[0], output_len=len(tv[1]))
    assert got == tv[1]


def test_evaluate_python_infers_output_len_from_cipher_outputs(built_speck):
    cipher, tv = built_speck
    with redirect_stdout(io.StringIO()):
        got = imp.evaluate_python(cipher, tv[0])  # output_len=None -> inferred from cipher.outputs
    assert got == tv[1]


def test_evaluate_python_raises_for_unbuilt_module():
    cipher = SPECK_PERMUTATION(r=None, version=32)
    with pytest.raises(ModuleNotFoundError):
        with redirect_stdout(io.StringIO()):
            imp.evaluate_python(cipher, [[0, 0]], cipher_name="THIS_IMPL_MODULE_DOES_NOT_EXIST_KAT")


# ----------------------------- test_implementation_python: None / True / False -----------------------------
def test_implementation_python_returns_none_when_file_missing():
    cipher = SPECK_PERMUTATION(r=None, version=32)
    with redirect_stdout(io.StringIO()):
        res = imp.test_implementation_python(cipher, "UNBUILT_IMPL_NAME_KAT", [[0, 0]], [0, 0])
    assert res is None


def test_implementation_python_true_on_match_false_on_mismatch(built_speck):
    cipher, tv = built_speck
    with redirect_stdout(io.StringIO()):
        ok = imp.test_implementation_python(cipher, cipher.name, tv[0], tv[1])
        bad = imp.test_implementation_python(cipher, cipher.name, tv[0], [w ^ 1 for w in tv[1]])
    assert ok is True
    assert bad is False
