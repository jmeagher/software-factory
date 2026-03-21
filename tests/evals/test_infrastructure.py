"""Tests for the test infrastructure itself: fixtures, markers, and run-all.sh."""
import os
import subprocess
import stat
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Tests for mem_env fixture
# ---------------------------------------------------------------------------


def test_mem_env_sets_claude_plugin_data(mem_env, tmp_path):
    assert "CLAUDE_PLUGIN_DATA" in mem_env
    assert mem_env["CLAUDE_PLUGIN_DATA"] == str(tmp_path)


def test_mem_env_returns_env_dict(mem_env):
    assert isinstance(mem_env, dict)
    # Should inherit from os.environ, so PATH must be present
    assert "PATH" in mem_env


# ---------------------------------------------------------------------------
# Tests for memory_script fixture
# ---------------------------------------------------------------------------


def test_memory_script_returns_path(memory_script):
    assert isinstance(memory_script, Path)


def test_memory_script_exists(memory_script):
    assert memory_script.exists(), f"memory.py not found at {memory_script}"


def test_memory_script_is_named_correctly(memory_script):
    assert memory_script.name == "memory.py"


# ---------------------------------------------------------------------------
# Tests for telemetry_script fixture
# ---------------------------------------------------------------------------


def test_telemetry_script_returns_path(telemetry_script):
    assert isinstance(telemetry_script, Path)


def test_telemetry_script_exists(telemetry_script):
    assert telemetry_script.exists(), f"telemetry.py not found at {telemetry_script}"


def test_telemetry_script_is_named_correctly(telemetry_script):
    assert telemetry_script.name == "telemetry.py"


# ---------------------------------------------------------------------------
# Tests for skill_doc fixture
# ---------------------------------------------------------------------------


def test_skill_doc_returns_string(skill_doc):
    text = skill_doc("jsf-workflow")
    assert isinstance(text, str)


def test_skill_doc_has_content(skill_doc):
    text = skill_doc("jsf-workflow")
    assert len(text) > 0


def test_skill_doc_for_all_skills(skill_doc):
    skills = [
        "jsf-clarification",
        "jsf-memory-protocol",
        "jsf-otel-tracing",
        "jsf-spec-planning",
        "jsf-tdd-implementation",
        "jsf-validation-gate",
        "jsf-workflow",
    ]
    for skill in skills:
        text = skill_doc(skill)
        assert len(text) > 0, f"skill_doc returned empty string for {skill}"


# ---------------------------------------------------------------------------
# Tests for command_doc fixture
# ---------------------------------------------------------------------------


def test_command_doc_returns_string(command_doc):
    text = command_doc("start")
    assert isinstance(text, str)


def test_command_doc_has_content(command_doc):
    text = command_doc("start")
    assert len(text) > 0


def test_command_doc_for_all_commands(command_doc):
    for cmd in ["start", "resume", "status"]:
        text = command_doc(cmd)
        assert len(text) > 0, f"command_doc returned empty string for {cmd}"


# ---------------------------------------------------------------------------
# Tests for hook_script fixture
# ---------------------------------------------------------------------------


def test_hook_script_returns_path(hook_script):
    p = hook_script("block-dangerous-bash.sh")
    assert isinstance(p, Path)


def test_hook_script_exists(hook_script):
    p = hook_script("block-dangerous-bash.sh")
    assert p.exists(), f"hook script not found at {p}"


def test_hook_script_all_three(hook_script):
    for name in [
        "block-dangerous-bash.sh",
        "block-dangerous-git.sh",
        "block-dangerous-sql.sh",
    ]:
        p = hook_script(name)
        assert p.exists(), f"hook script not found: {name}"


# ---------------------------------------------------------------------------
# Tests for --run-llm-evals flag and llm_eval marker
# ---------------------------------------------------------------------------


def test_llm_eval_marker_is_registered():
    """The llm_eval marker should be registered (no warnings about unknown marks)."""
    result = subprocess.run(
        ["python3", "-m", "pytest", "--markers"],
        capture_output=True,
        text=True,
        cwd="/home/jmeagher/devel/software-factory",
    )
    assert "llm_eval" in result.stdout


def test_run_llm_evals_option_is_registered():
    """--run-llm-evals option should not cause an error when passed."""
    result = subprocess.run(
        [
            "python3",
            "-m",
            "pytest",
            "--run-llm-evals",
            "--collect-only",
            "-q",
            "tests/evals/",
        ],
        capture_output=True,
        text=True,
        cwd="/home/jmeagher/devel/software-factory",
    )
    # Should not error with "unrecognized arguments"
    assert "unrecognized arguments" not in result.stderr
    assert "error: unrecognized" not in result.stderr


# ---------------------------------------------------------------------------
# Tests for run-all.sh
# ---------------------------------------------------------------------------

RUN_ALL = Path("/home/jmeagher/devel/software-factory/tests/evals/run-all.sh")


def test_run_all_sh_exists():
    assert RUN_ALL.exists(), "tests/evals/run-all.sh does not exist"


def test_run_all_sh_is_executable():
    assert os.access(RUN_ALL, os.X_OK), "run-all.sh is not executable"


def test_run_all_sh_is_shell_script():
    content = RUN_ALL.read_text()
    assert content.startswith("#!/"), "run-all.sh must start with a shebang"


def test_run_all_sh_runs_pytest():
    content = RUN_ALL.read_text()
    assert "pytest" in content, "run-all.sh must invoke pytest"


def test_run_all_sh_exits_nonzero_on_failure():
    """run-all.sh should use set -e or explicit exit code propagation."""
    content = RUN_ALL.read_text()
    # Either set -e or explicit exit propagation
    assert "set -e" in content or "exit " in content or '$?' in content


# ---------------------------------------------------------------------------
# Sample llm_eval-marked test (should be skipped without --run-llm-evals)
# ---------------------------------------------------------------------------


@pytest.mark.llm_eval
def test_llm_eval_sample_is_skipped_without_flag():
    """This test verifies that llm_eval tests are properly skipped."""
    # If we get here without --run-llm-evals, the test should have been skipped
    pytest.fail("llm_eval test ran without --run-llm-evals flag")
