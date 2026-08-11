from __future__ import annotations

import subprocess
import sys
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_documented_editable_install_command() -> None:
    readme = (ROOT / "README.md").read_text()
    match = re.search(
        r"python -m pip install -e ['\"](\.\[[^]]+\])['\"]",
        readme,
    )
    assert match is not None, "README has no editable install command"
    editable_spec = match.group(1)
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", editable_spec],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert result.returncode == 0, output
    assert "does not provide the extra" not in output

    pytest_check = subprocess.run(
        [sys.executable, "-m", "pytest", "--version"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert pytest_check.returncode == 0, pytest_check.stdout + pytest_check.stderr
