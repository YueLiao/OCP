"""Shared filesystem paths for OCP runtime artifacts.

The default behavior remains compatible with the original project: runtime
artifacts are written under ``<repo>/files``. Set ``OCP_FILES_DIR`` to redirect
generated models, trails, implementations, and temporary modeling files.
"""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILES_DIR = PROJECT_ROOT / "files"


def get_files_dir(*parts, create=True):
    """Return the configured OCP files directory, optionally with subpaths."""
    base = Path(os.environ.get("OCP_FILES_DIR", DEFAULT_FILES_DIR)).expanduser()
    path = base.joinpath(*parts)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path
