import importlib
from typing import Any, Dict

from agent.types import SkillName, SkillRequest, SkillResult
from agent.session import Session
from agent.skills.base import BaseSkill


# Catalog of all supported ciphers with their module paths and factory functions.
# Each entry maps: cipher_name -> { module, factories: { type_name: factory_function_name }, default_version }
CIPHER_CATALOG = {
    "speck": {
        "module": "primitives.speck",
        "factories": {
            "permutation": "SPECK_PERMUTATION",
            "blockcipher": "SPECK_BLOCKCIPHER",
        },
        "default_version": {"permutation": 32, "blockcipher": [32, 64]},
        "valid_versions": {
            "permutation": [32, 48, 64, 96, 128],
            "blockcipher": [[32, 64], [48, 72], [48, 96], [64, 96], [64, 128],
                            [96, 96], [96, 144], [128, 128], [128, 192], [128, 256]],
        },
    },
    "aes": {
        "module": "primitives.aes",
        "factories": {
            "permutation": "AES_PERMUTATION",
            "blockcipher": "AES_BLOCKCIPHER",
        },
        "default_version": {"permutation": None, "blockcipher": [128, 128]},
        "valid_versions": {
            "blockcipher": [[128, 128], [128, 192], [128, 256]],
        },
    },
    "gift": {
        "module": "primitives.gift",
        "factories": {
            "permutation": "GIFT_PERMUTATION",
            "blockcipher": "GIFT_BLOCKCIPHER",
        },
        "default_version": {"permutation": 64, "blockcipher": [64, 128]},
        "valid_versions": {
            "permutation": [64, 128],
            "blockcipher": [[64, 128]],
        },
    },
    "simon": {
        "module": "primitives.simon",
        "factories": {
            "permutation": "SIMON_PERMUTATION",
            "blockcipher": "SIMON_BLOCKCIPHER",
        },
        "default_version": {"permutation": 32, "blockcipher": [32, 64]},
        "valid_versions": {
            "permutation": [32, 48, 64, 96, 128],
            "blockcipher": [[32, 64], [48, 72], [48, 96], [64, 96], [64, 128],
                            [96, 96], [96, 144], [128, 128], [128, 192], [128, 256]],
        },
    },
    "present": {
        "module": "primitives.present",
        "factories": {
            "permutation": "PRESENT_PERMUTATION",
            "blockcipher": "PRESENT_BLOCKCIPHER",
        },
        "default_version": {"permutation": None, "blockcipher": [64, 80]},
        "valid_versions": {
            "blockcipher": [[64, 80], [64, 128]],
        },
    },
    "skinny": {
        "module": "primitives.skinny",
        "factories": {
            "permutation": "SKINNY_PERMUTATION",
            "blockcipher": "SKINNY_BLOCKCIPHER",
        },
        "default_version": {"permutation": 64, "blockcipher": [64, 64]},
        "valid_versions": {
            "permutation": [64, 128],
            "blockcipher": [[64, 64], [64, 128], [64, 192], [128, 128], [128, 256], [128, 384]],
        },
    },
    "ascon": {
        "module": "primitives.ascon",
        "factories": {
            "permutation": "ASCON_PERMUTATION",
        },
        "default_version": {"permutation": None},
    },
    "chacha": {
        "module": "primitives.chacha",
        "factories": {
            "permutation": "CHACHA_PERMUTATION",
            "keypermutation": "CHACHA_KEYPERMUTATION",
        },
        "default_version": {"permutation": None, "keypermutation": None},
    },
    "salsa": {
        "module": "primitives.salsa",
        "factories": {
            "permutation": "SALSA_PERMUTATION",
            "keypermutation": "SALSA_KEYPERMUTATION",
        },
        "default_version": {"permutation": None, "keypermutation": None},
    },
    "forro": {
        "module": "primitives.forro",
        "factories": {
            "permutation": "FORRO_PERMUTATION",
            "keypermutation": "FORRO_KEYPERMUTATION",
        },
        "default_version": {"permutation": None, "keypermutation": None},
    },
    "led": {
        "module": "primitives.led",
        "factories": {
            "permutation": "LED_PERMUTATION",
            "blockcipher": "LED_BLOCKCIPHER",
        },
        "default_version": {"permutation": None, "blockcipher": [64, 64]},
        "valid_versions": {
            "blockcipher": [[64, 64], [64, 128]],
        },
    },
    "siphash": {
        "module": "primitives.siphash",
        "factories": {
            "permutation": "SIPHASH_PERMUTATION",
        },
        "default_version": {"permutation": None},
    },
    "shacal2": {
        "module": "primitives.shacal2",
        "factories": {
            "blockcipher": "SHACAL2_BLOCKCIPHER",
        },
        "default_version": {"blockcipher": None},
    },
    "rocca": {
        "module": "primitives.rocca",
        "factories": {
            "permutation": "ROCCA_AD_PERMUTATION",
        },
        "default_version": {"permutation": None},
    },
    "speedy": {
        "module": "primitives.speedy",
        "factories": {
            "permutation": "SPEEDY_PERMUTATION",
        },
        "default_version": {"permutation": None},
    },
}


class CipherInstantiationSkill(BaseSkill):

    @property
    def name(self) -> SkillName:
        return SkillName.CIPHER_INSTANTIATION

    @property
    def description(self) -> str:
        return (
            "Instantiate a cryptographic cipher primitive. "
            "Supported ciphers: " + ", ".join(sorted(CIPHER_CATALOG.keys())) + ". "
            "Types: permutation, blockcipher, keypermutation."
        )

    @property
    def param_schema(self) -> Dict[str, Any]:
        return {
            "cipher_name": {
                "type": "string",
                "required": True,
                "description": "Name of the cipher (e.g., 'speck', 'aes', 'gift')",
                "enum": sorted(CIPHER_CATALOG.keys()),
            },
            "cipher_type": {
                "type": "string",
                "required": False,
                "default": "blockcipher",
                "description": "Type: 'permutation', 'blockcipher', or 'keypermutation'",
            },
            "version": {
                "type": "any",
                "required": False,
                "description": "Version parameter (int for permutations, list for blockciphers)",
            },
            "rounds": {
                "type": "int",
                "required": False,
                "description": "Number of rounds (None for default)",
            },
        }

    def execute(self, request: SkillRequest, session: Session) -> SkillResult:
        params = request.params
        cipher_name = params.get("cipher_name", "").lower()
        cipher_type = params.get("cipher_type", "blockcipher").lower()
        version = params.get("version")
        rounds = params.get("rounds")

        if cipher_name not in CIPHER_CATALOG:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Unknown cipher: '{cipher_name}'. Supported: {sorted(CIPHER_CATALOG.keys())}",
            )

        entry = CIPHER_CATALOG[cipher_name]

        # Auto-detect cipher_type if only one factory exists
        if cipher_type not in entry["factories"]:
            available = list(entry["factories"].keys())
            if len(available) == 1:
                cipher_type = available[0]
            else:
                return SkillResult(
                    success=False,
                    skill=self.name,
                    error=f"Cipher type '{cipher_type}' not available for {cipher_name}. Available: {available}",
                )

        factory_name = entry["factories"][cipher_type]
        module_path = entry["module"]

        # Build kwargs
        kwargs = {}
        if rounds is not None:
            kwargs["r"] = rounds
        if version is not None:
            kwargs["version"] = version

        try:
            mod = importlib.import_module(module_path)
            factory_fn = getattr(mod, factory_name)
            cipher = factory_fn(**kwargs)
            session.set_cipher(cipher)
            return SkillResult(
                success=True,
                skill=self.name,
                data={"cipher_name": cipher.name, "type": cipher_type},
                summary=f"Created cipher: {cipher.name}",
            )
        except Exception as e:
            return SkillResult(
                success=False,
                skill=self.name,
                error=f"Failed to instantiate {cipher_name}: {e}",
            )
