from agent import CipherSpec, LayerSpec, OCPAgent


def test_custom_cipher_definition_validates_missing_round_structure():
    agent = OCPAgent()
    spec = CipherSpec(name="Incomplete", round_structure=[])

    result = agent.define_custom_cipher(spec)

    assert not result.success
    assert "round_structure must have at least one layer" in result.error


def test_custom_cipher_definition_builds_tiny_arx_permutation():
    agent = OCPAgent()
    spec = CipherSpec(
        name="TinyARX",
        cipher_type="permutation",
        block_size=32,
        word_bitsize=16,
        nbr_words=2,
        nbr_rounds=2,
        round_structure=[
            LayerSpec("rotation", {"direction": "r", "amount": 7, "word_index": 0}),
            LayerSpec("modadd", {"input_indices": [[0, 1]], "output_indices": [0]}),
            LayerSpec("rotation", {"direction": "l", "amount": 2, "word_index": 1}),
            LayerSpec("xor", {"input_indices": [[0, 1]], "output_indices": [1]}),
        ],
    )

    result = agent.define_custom_cipher(spec)

    assert result.success
    assert result.data["cipher_name"] == "TinyARX_PERM"
    assert agent.session.get_cipher().name == "TinyARX_PERM"
