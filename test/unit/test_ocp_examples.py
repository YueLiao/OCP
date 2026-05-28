from types import SimpleNamespace

import OCP


def test_generated_implementation_helper_reports_missing_vectors(monkeypatch, tmp_path):
    calls = []

    def fake_generate(cipher, output_path, language, unroll=False):
        calls.append((output_path, language, unroll))

    monkeypatch.setattr(OCP, "FILES_DIR", tmp_path)
    monkeypatch.setattr(OCP.imp, "generate_implementation", fake_generate)
    cipher = SimpleNamespace(name="Toy", test_vectors=[])

    assert not OCP.test_python_unrolled_imp(cipher)
    assert calls == [(tmp_path / "Toy_unrolled.py", "python", True)]


def test_generated_implementation_helper_runs_each_test_vector(monkeypatch, tmp_path):
    generated = []
    tested = []

    def fake_generate(cipher, output_path, language, unroll=False):
        generated.append((output_path, language, unroll))

    def fake_tester(cipher, implementation_name, plaintext, ciphertext):
        tested.append((implementation_name, plaintext, ciphertext))

    monkeypatch.setattr(OCP, "FILES_DIR", tmp_path)
    monkeypatch.setattr(OCP.imp, "generate_implementation", fake_generate)
    cipher = SimpleNamespace(name="Toy", test_vectors=[("p0", "c0"), ("p1", "c1")])

    assert OCP._test_generated_implementation(cipher, "c", "c", fake_tester)
    assert generated == [(tmp_path / "Toy.c", "c", False)]
    assert tested == [("Toy", "p0", "c0"), ("Toy", "p1", "c1")]
