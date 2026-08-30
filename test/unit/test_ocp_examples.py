from types import SimpleNamespace

import pytest
from _pytest.outcomes import Skipped

import OCP


def test_generated_implementation_helper_skips_when_no_vectors(monkeypatch, tmp_path):
    calls = []

    def fake_generate(cipher, output_path, language, unroll=False):
        calls.append((output_path, language, unroll))

    monkeypatch.setattr(OCP, "FILES_DIR", tmp_path)
    monkeypatch.setattr(OCP.imp, "generate_implementation", fake_generate)
    cipher = SimpleNamespace(name="Toy", test_vectors=[])

    with pytest.raises(Skipped):  # a cipher with no vectors is skipped, not silently passed
        OCP.test_python_unrolled_imp(cipher)
    assert calls == [(tmp_path / "Toy_unrolled.py", "python", True)]  # generation still happened first


def test_generated_implementation_helper_runs_each_test_vector(monkeypatch, tmp_path):
    generated = []
    tested = []

    def fake_generate(cipher, output_path, language, unroll=False):
        generated.append((output_path, language, unroll))

    def fake_tester(cipher, implementation_name, plaintext, ciphertext):
        tested.append((implementation_name, plaintext, ciphertext))
        return True  # every vector matches

    monkeypatch.setattr(OCP, "FILES_DIR", tmp_path)
    monkeypatch.setattr(OCP.imp, "generate_implementation", fake_generate)
    cipher = SimpleNamespace(name="Toy", test_vectors=[("p0", "c0"), ("p1", "c1")])

    assert OCP._test_generated_implementation(cipher, "c", "c", fake_tester) is True
    assert generated == [(tmp_path / "Toy.c", "c", False)]
    assert tested == [("Toy", "p0", "c0"), ("Toy", "p1", "c1")]


def test_generated_implementation_helper_asserts_on_mismatch(monkeypatch, tmp_path):
    monkeypatch.setattr(OCP, "FILES_DIR", tmp_path)
    monkeypatch.setattr(OCP.imp, "generate_implementation", lambda *a, **k: None)
    cipher = SimpleNamespace(name="Toy", test_vectors=[("p0", "c0")])

    # a tester that reports a wrong result (False) must fail the test, not pass silently
    with pytest.raises(AssertionError, match="does not"):
        OCP._test_generated_implementation(cipher, "python", "py", lambda *a, **k: False)


def test_generated_implementation_helper_skips_when_backend_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(OCP, "FILES_DIR", tmp_path)
    monkeypatch.setattr(OCP.imp, "generate_implementation", lambda *a, **k: None)
    cipher = SimpleNamespace(name="Toy", test_vectors=[("p0", "c0")])

    # a tester returning None (e.g. missing C toolchain / unbuilt file) skips, not fails
    with pytest.raises(Skipped):
        OCP._test_generated_implementation(cipher, "c", "c", lambda *a, **k: None)
