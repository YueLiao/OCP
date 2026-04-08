from pathlib import Path
from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill

DEFAULT_OUTPUT_DIR = Path("files")


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
                "default": "files",
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
        output_dir = Path(params.get("output_dir", "files"))
        output_dir.mkdir(parents=True, exist_ok=True)

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
            imp.generate_implementation(cipher, filename, language, unroll)
            results_data = {"filename": str(filename), "language": language, "unrolled": unroll}

            # Run tests if requested
            test_results = []
            if test and cipher.test_vectors:
                test_fn_map = {
                    "python": imp.test_implementation_python,
                    "c": imp.test_implementation_c,
                    "verilog": imp.test_implementation_verilog,
                }
                test_fn = test_fn_map[language]
                impl_name = cipher.name + suffix
                for tv in cipher.test_vectors:
                    try:
                        test_fn(cipher, impl_name, tv[0], tv[1])
                        test_results.append(True)
                    except Exception as e:
                        test_results.append(str(e))

                results_data["test_results"] = test_results
                passed = sum(1 for r in test_results if r is True)
                total = len(test_results)
                summary = f"Generated {language} code: {filename}. Tests: {passed}/{total} passed."
            else:
                summary = f"Generated {language} code: {filename}."

            return SkillResult(
                success=True,
                skill=self.name,
                data=results_data,
                summary=summary,
            )
        except Exception as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Code generation failed: {e}",
            )
