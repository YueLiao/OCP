from agent.agentic import requires_confirmation
from agent.llm.provider import LLMProvider
from agent.interfaces.api import OCPAgent
from agent.skills import SkillRegistry
from agent.skills.base import BaseSkill
from agent.types import SkillName, SkillRequest, SkillResult, UserIntent


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


class FakeArtifactSkill(BaseSkill):
    @property
    def name(self):
        return SkillName.CODE_GENERATION

    @property
    def description(self):
        return "fake artifact skill"

    @property
    def param_schema(self):
        return {}

    def execute(self, request, session):
        return SkillResult(
            success=True,
            skill=self.name,
            data={"artifact_links": [{"label": "generated_code", "path": "/tmp/generated.py"}]},
            summary="generated",
        )


class FakeIntentProvider(LLMProvider):
    def parse_user_request(self, user_message, conversation_history, available_skills, session_context):
        return UserIntent(requests=[SkillRequest(skill=SkillName.CODE_GENERATION)])

    def generate_response(self, results, original_intent, conversation_history, session_context):
        return "done"

    def handle_error(self, error, failed_request, session_context):
        return str(error)


def test_chat_skill_execution_registers_artifacts():
    registry = SkillRegistry()
    registry.register(FakeArtifactSkill())
    agent = OCPAgent(llm_provider=FakeIntentProvider(), skill_registry=registry)

    response = agent.chat("generate")

    assert response == "done"
    assert agent.session.get_results()[0].summary == "generated"
    assert agent.session.get_context()["artifact_count"] == 1
    assert agent.session.get_artifacts()[0]["label"] == "generated_code"
