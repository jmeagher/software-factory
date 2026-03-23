"""
Phase 1 TDD tests: rename skill directories and update SKILL.md name fields.

These tests verify:
1. New directories exist (without jsf- prefix)
2. Old directories do NOT exist (with jsf- prefix)
3. Each SKILL.md has the correct name: field (without jsf- prefix)
"""
import os
import re
import pytest

SKILLS_DIR = "/home/jmeagher/devel/software-factory/skills"

SKILL_RENAMES = [
    ("jsf-clarification", "clarification"),
    ("jsf-memory-protocol", "memory-protocol"),
    ("jsf-otel-tracing", "otel-tracing"),
    ("jsf-spec-planning", "spec-planning"),
    ("jsf-tdd-implementation", "tdd-implementation"),
    ("jsf-validation-gate", "validation-gate"),
    ("jsf-workflow", "workflow"),
]


@pytest.mark.parametrize("old_name, new_name", SKILL_RENAMES)
def test_new_skill_directory_exists(old_name, new_name):
    """New directory (without jsf- prefix) must exist."""
    new_dir = os.path.join(SKILLS_DIR, new_name)
    assert os.path.isdir(new_dir), f"Expected directory {new_dir} to exist"


@pytest.mark.parametrize("old_name, new_name", SKILL_RENAMES)
def test_old_skill_directory_does_not_exist(old_name, new_name):
    """Old directory (with jsf- prefix) must not exist."""
    old_dir = os.path.join(SKILLS_DIR, old_name)
    assert not os.path.exists(old_dir), f"Old directory {old_dir} should not exist"


@pytest.mark.parametrize("old_name, new_name", SKILL_RENAMES)
def test_skill_md_name_field_updated(old_name, new_name):
    """SKILL.md name: field must match the new name (without jsf- prefix)."""
    skill_md = os.path.join(SKILLS_DIR, new_name, "SKILL.md")
    assert os.path.isfile(skill_md), f"SKILL.md not found at {skill_md}"

    with open(skill_md) as f:
        content = f.read()

    # Find the name: field in frontmatter
    match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
    assert match is not None, f"Could not find 'name:' field in {skill_md}"
    actual_name = match.group(1).strip()
    assert actual_name == new_name, (
        f"Expected name: {new_name} in {skill_md}, got: {actual_name}"
    )


@pytest.mark.parametrize("old_name, new_name", SKILL_RENAMES)
def test_skill_md_name_does_not_have_jsf_prefix(old_name, new_name):
    """SKILL.md name: field must not start with 'jsf-'."""
    skill_md = os.path.join(SKILLS_DIR, new_name, "SKILL.md")
    if not os.path.isfile(skill_md):
        pytest.skip(f"SKILL.md not found (directory may not be renamed yet)")

    with open(skill_md) as f:
        content = f.read()

    match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
    if match is None:
        pytest.skip("No name: field found")

    actual_name = match.group(1).strip()
    assert not actual_name.startswith("jsf-"), (
        f"name: field in {skill_md} still has jsf- prefix: {actual_name}"
    )
