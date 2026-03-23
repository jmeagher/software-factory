"""Shared fixtures and pytest configuration for tests/evals/.

Run from repo root: python3 -m pytest tests/evals/ -v
To include LLM-gated tests: python3 -m pytest tests/evals/ -v --run-llm-evals
"""
import os
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Plugin cache paths
# ---------------------------------------------------------------------------

_REPO_ROOT = Path("/home/jmeagher/devel/software-factory")
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_SKILLS_DIR = _REPO_ROOT / "skills"
_HOOKS_SCRIPTS_DIR = _REPO_ROOT / "hooks" / "scripts"
_COMMANDS_DIR = _REPO_ROOT / "commands"


# ---------------------------------------------------------------------------
# pytest option and marker registration
# ---------------------------------------------------------------------------


def pytest_addoption(parser):
    parser.addoption(
        "--run-llm-evals",
        action="store_true",
        default=False,
        help="Run tests marked with @pytest.mark.llm_eval (requires ANTHROPIC_API_KEY).",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "llm_eval: mark test as an LLM invocation eval (skipped unless --run-llm-evals is passed).",
    )


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-llm-evals"):
        skip = pytest.mark.skip(reason="Pass --run-llm-evals to run LLM eval tests.")
        for item in items:
            if item.get_closest_marker("llm_eval"):
                item.add_marker(skip)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mem_env(tmp_path):
    """Return an env dict with CLAUDE_PLUGIN_DATA set to tmp_path.

    Matches the pattern used in tests/memory/test_memory.py.
    """
    return {**os.environ, "CLAUDE_PLUGIN_DATA": str(tmp_path), "SF_AGENT_ID": "test"}


@pytest.fixture
def memory_script():
    """Return Path to scripts/memory.py in the plugin cache."""
    return _SCRIPTS_DIR / "memory.py"


@pytest.fixture
def telemetry_script():
    """Return Path to scripts/telemetry.py in the plugin cache."""
    return _SCRIPTS_DIR / "telemetry.py"


@pytest.fixture
def skill_doc():
    """Return a callable that reads a skill's SKILL.md text.

    Usage::

        def test_something(skill_doc):
            text = skill_doc("workflow")
    """

    def _get(skill_name: str) -> str:
        path = _SKILLS_DIR / skill_name / "SKILL.md"
        return path.read_text()

    return _get


@pytest.fixture
def command_doc():
    """Return a callable that reads a command's .md text.

    Usage::

        def test_something(command_doc):
            text = command_doc("start")
    """

    def _get(command_name: str) -> str:
        path = _COMMANDS_DIR / f"{command_name}.md"
        return path.read_text()

    return _get


@pytest.fixture
def hook_script():
    """Return a callable that resolves a hook script Path by name.

    Usage::

        def test_something(hook_script):
            p = hook_script("block-dangerous-bash.sh")
    """

    def _get(hook_name: str) -> Path:
        return _HOOKS_SCRIPTS_DIR / hook_name

    return _get
