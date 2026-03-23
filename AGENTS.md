# Claude Code Instructions: John's Software Factory (jsf)

## Architecture Reference

**Before making any changes to this repository, read `Architecture.md`** at the repo root. It describes every component in the plugin: skills, agents, commands, rules, hooks, scripts, and tests — including naming conventions and how they relate to each other.

## Keeping Architecture.md in Sync

`Architecture.md` must always reflect the current implementation. Update it whenever you:

- Add, remove, or rename a skill, agent, command, or rule
- Change what a component does (its purpose or behavioral contract)
- Add or remove scripts, hook scripts, or test categories
- Change dispatch strings or naming conventions
- Add or remove files that are part of the plugin's public surface

Update `Architecture.md` in the same commit as the implementation change — never leave it stale. If you are unsure whether a change affects the architecture, err on the side of updating it.

## Naming Convention

Within the `jsf` plugin namespace, component names do **not** repeat the `jsf-` prefix:

- Skill directories: `skills/clarification/`, not `skills/jsf-clarification/`
- Agent dispatch strings: `jsf:clarifier`, not `jsf:jsf-clarifier`
- Rule files (`rules/jsf-*.mdc`) are the exception — they are Cursor-compatible files that are **not** namespaced by the plugin system and must keep the prefix to avoid collisions.
