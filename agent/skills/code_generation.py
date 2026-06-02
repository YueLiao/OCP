from pathlib import Path
from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill
from tools.paths import get_files_dir


def _run_single_test_vector(test_fn, cipher, impl_name, test_vector):
    """Run one generated implementation test vector and return True or a failure message."""

    try:
        test_fn(cipher, impl_name, test_vector[0], test_vector[1])
        return True
    except Exception as exc:
        return str(exc)


def _run_generated_implementation_tests(imp, cipher, language, impl_name):
    """Run generated implementation tests while preserving legacy result entries."""

    test_fn_map = {
        "python": imp.test_implementation_python,
        "c": imp.test_implementation_c,
        "verilog": imp.test_implementation_verilog,
    }
    test_fn = test_fn_map[language]
    return [
        _run_single_test_vector(test_fn, cipher, impl_name, test_vector)
        for test_vector in cipher.test_vectors
    ]


class CodeGenerationSkill(BaseSkill):

    @property
    def name(self) -> SkillName:
        return SkillName.CODE_GENERATION

    @property
    def description(self) -> str:
        return (
            "Generate implementation code for the current cipher. "
            "Supports Python, C, and Verilog. Can generate compact or unrolled versions. "
            "Optionally runs test vectors to verify correctness."
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "language": {
                "type": "string",
                "required": True,
                "description": "Target language: 'python', 'c', or 'verilog'",
                "enum": ["python", "c", "verilog"],
            },
            "unroll": {
                "type": "bool",
                "required": False,
                "default": False,
                "description": "Whether to generate unrolled implementation",
            },
            "test": {
                "type": "bool",
                "required": False,
                "default": True,
                "description": "Whether to run test vectors after generation",
            },
            "output_dir": {
                "type": "string",
                "required": False,
                "default": "OCP_FILES_DIR or files/",
                "description": "Output directory for generated files",
            },
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        import implementations.implementations as imp

        cipher = session.get_cipher()
        if cipher is None:
            return SkillResult(
                success=False,
                skill=self.name,
                error="No cipher loaded. Use cipher_instantiation first.",
            )

        params = request.params
        language = params.get("language", "python").lower()
        unroll = params.get("unroll", False)
        test = params.get("test", True)
        output_dir_param = params.get("output_dir")
        output_dir = Path(output_dir_param) if output_dir_param else get_files_dir()

        if language not in ("python", "c", "verilog"):
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Unsupported language: '{language}'. Use 'python', 'c', or 'verilog'.",
            )

        ext_map = {"python": ".py", "c": ".c", "verilog": ".sv"}
        suffix = "_unrolled" if unroll else ""
        filename = output_dir / f"{cipher.name}{suffix}{ext_map[language]}"

        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            imp.generate_implementation(cipher, filename, language, unroll)
            results_data = {
                "filename": str(filename),
                "language": language,
                "unrolled": unroll,
                "artifact_links": [{"label": "generated_code", "path": str(filename)}],
            }

            # Run tests if requested
            if test and cipher.test_vectors:
                impl_name = cipher.name + suffix
                test_results = _run_generated_implementation_tests(imp, cipher, language, impl_name)
                results_data["test_results"] = test_results
                passed = sum(1 for r in test_results if r is True)
                total = len(test_results)
                results_data["test_summary"] = {
                    "passed": passed,
                    "total": total,
                    "failed": total - passed,
                }
                summary = f"Generated {language} code: {filename}. Tests: {passed}/{total} passed."
            else:
                summary = f"Generated {language} code: {filename}."

            return SkillResult(
                success=True,
                skill=self.name,
                data=results_data,
                summary=summary,
            )
        except (OSError, ValueError) as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Code generation failed: {e}",
            )
        except Exception as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Unexpected code generation failure: {e}",
            )
