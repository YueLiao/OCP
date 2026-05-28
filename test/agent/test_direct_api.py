from agent import OCPAgent


def test_direct_api_instantiates_builtin_cipher():
    agent = OCPAgent()

    result = agent.instantiate_cipher("speck", "blockcipher", version=[32, 64])

    assert result.success
    assert result.data == {"cipher_name": "SPECK32_64", "type": "blockcipher"}
    assert agent.session.get_cipher().name == "SPECK32_64"


def test_direct_api_reports_unknown_cipher():
    agent = OCPAgent()

    result = agent.instantiate_cipher("not_a_cipher")

    assert not result.success
    assert "Unknown cipher" in result.error


def test_direct_api_rejects_invalid_builtin_cipher_version():
    agent = OCPAgent()

    result = agent.instantiate_cipher("speck", "blockcipher", version=[31, 64])

    assert not result.success
    assert "Invalid version" in result.error
    assert "[32, 64]" in result.error
