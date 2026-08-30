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


class FailingSkill(BaseSkill):
    def __init__(self, exc):
        self.exc = exc

    @property
    def name(self):
        return SkillName.CODE_GENERATION

    @property
    def description(self):
        return "failing skill"

    @property
    def param_schema(self):
        return {}

    def execute(self, request, session):
        raise self.exc


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

    # Skill turns now return a deterministic aggregation of per-skill outcomes
    # (success -> `r.summary or "<skill>: done."`), not a provider-generated reply.
    assert response == "generated"
    assert agent.session.get_results()[0].summary == "generated"
    assert agent.session.get_context()["artifact_count"] == 1
    assert agent.session.get_artifacts()[0]["label"] == "generated_code"


def test_direct_skill_execution_classifies_expected_and_unexpected_failures():
    registry = SkillRegistry()
    registry.register(FailingSkill(ValueError("bad user input")))
    agent = OCPAgent(skill_registry=registry)

    result = agent.generate_code()

    assert not result.success
    assert result.error == "Skill 'code_generation' failed: bad user input"

    registry = SkillRegistry()
    registry.register(FailingSkill(TypeError("programming detail")))
    agent = OCPAgent(skill_registry=registry)

    result = agent.generate_code()

    assert not result.success
    assert result.error == "Unexpected skill 'code_generation' failed: programming detail"


def test_chat_skill_execution_keeps_provider_error_handler():
    registry = SkillRegistry()
    registry.register(FailingSkill(TypeError("provider should format this")))
    agent = OCPAgent(llm_provider=FakeIntentProvider(), skill_registry=registry)

    response = agent.chat("generate")

    # The provider's handle_error still formats the stored result.error (below);
    # the aggregated skill-turn response now renders a failed skill as
    # "<skill> failed: <error>" instead of the old provider generate_response reply.
    assert response == "code_generation failed: provider should format this"
    assert agent.session.get_results()[0].error == "provider should format this"


class FakeExtractionSkill(BaseSkill):
    @property
    def name(self):
        return SkillName.CIPHER_EXTRACTION

    @property
    def description(self):
        return "fake extraction skill"

    @property
    def param_schema(self):
        return {}

    def execute(self, request, session):
        session.set_metadata(
            "extraction_data",
            {
                "pipeline": "single",
                "file_type": "text",
                "file_name": "inline.txt",
                "full_text": "tiny arx",
            },
        )
        session.set_metadata("extraction_auto_build", True)
        return SkillResult(success=True, skill=self.name, summary="extracted")


class FakeDefinitionSkill(BaseSkill):
    @property
    def name(self):
        return SkillName.CIPHER_DEFINITION

    @property
    def description(self):
        return "fake definition skill"

    @property
    def param_schema(self):
        return {}

    def execute(self, request, session):
        return SkillResult(
            success=True,
            skill=self.name,
            data={"artifact_links": [{"label": "job_record", "path": "/tmp/auto-build.json"}]},
            summary="built",
        )


class FakeExtractionProvider(FakeIntentProvider):
    def parse_user_request(self, user_message, conversation_history, available_skills, session_context):
        return UserIntent(requests=[SkillRequest(skill=SkillName.CIPHER_EXTRACTION)])

    def call_llm(self, prompt, image_data=None):
        return """{
          "name": "TinyARX",
          "cipher_type": "permutation",
          "block_size": 32,
          "word_bitsize": 16,
          "nbr_words": 2,
          "nbr_rounds": 2,
          "round_structure": [
            {"layer_type": "rotation", "params": {"direction": "r", "amount": 7, "word_index": 0}},
            {"layer_type": "xor", "params": {"input_indices": [[0, 1]], "output_indices": [1]}}
          ]
        }"""


class InvalidExtractionProvider(FakeExtractionProvider):
    def call_llm(self, prompt, image_data=None):
        return "not json"


class UnexpectedExtractionProvider(FakeExtractionProvider):
    def call_llm(self, prompt, image_data=None):
        raise TypeError("programming detail")


def test_auto_build_extraction_result_is_recorded_once_with_artifacts():
    registry = SkillRegistry()
    registry.register(FakeExtractionSkill())
    registry.register(FakeDefinitionSkill())
    agent = OCPAgent(llm_provider=FakeExtractionProvider(), skill_registry=registry)

    response = agent.chat("extract and build")

    # Aggregated summaries: extraction ("extracted") then the auto-build ("built").
    assert response == "extracted\nbuilt"
    assert [result.skill for result in agent.session.get_results()] == [
        SkillName.CIPHER_EXTRACTION,
        SkillName.CIPHER_DEFINITION,
    ]
    assert agent.session.get_context()["artifact_count"] == 1
    assert agent.session.get_artifacts()[0]["label"] == "job_record"


def test_extraction_pipeline_classifies_parse_and_unexpected_failures():
    registry = SkillRegistry()
    registry.register(FakeExtractionSkill())
    agent = OCPAgent(llm_provider=InvalidExtractionProvider(), skill_registry=registry)

    response = agent.chat("extract and build")

    # Extraction succeeds ("extracted"); the auto pipeline fails to parse the
    # "not json" reply, rendered as "<skill> failed: <error>" in the aggregation.
    assert response == (
        "extracted\ncipher_extraction failed: Extraction pipeline failed: "
        "No parseable JSON object found in LLM response: not json"
    )
    assert agent.session.get_results()[1].error.startswith("Extraction pipeline failed:")

    registry = SkillRegistry()
    registry.register(FakeExtractionSkill())
    agent = OCPAgent(llm_provider=UnexpectedExtractionProvider(), skill_registry=registry)

    response = agent.chat("extract and build")

    assert response == (
        "extracted\ncipher_extraction failed: "
        "Unexpected extraction pipeline failure: programming detail"
    )
    assert agent.session.get_results()[1].error == (
        "Unexpected extraction pipeline failure: programming detail"
    )
