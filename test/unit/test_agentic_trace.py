from agent.agentic import requires_confirmation
from agent.interfaces.api import OCPAgent


def test_direct_skill_execution_records_trace():
    agent = OCPAgent()

    result = agent.instantiate_cipher("speck", "blockcipher", version=[32, 64], rounds=1)
    trace = agent.session.get_trace()

    assert result.success
    assert trace[0]["event"] == "skill_start"
    assert trace[0]["payload"]["skill"] == "cipher_instantiation"
    assert trace[1]["event"] == "skill_finish"
    assert trace[1]["payload"]["success"] is True
    assert "artifact_count" in trace[1]["payload"]
    assert agent.session.get_context()["trace_length"] == 2


def test_risky_action_confirmation_policy_is_explicit():
    assert requires_confirmation("analyze")
    assert requires_confirmation("code")
    assert requires_confirmation("visualize")
    assert not requires_confirmation("draft")
