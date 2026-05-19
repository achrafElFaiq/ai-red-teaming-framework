# Plugin Development

This document describes the current plugin model used by the framework.

## Scope

Plugins are responsible for framework-specific attack construction and runtime integration.

The framework currently includes built-in plugins for:

- `pyrit`
- `garak`

Campaign YAML uses those exact framework names.

## Plugin registry

The registry lives in:

- `src/redteaming/plugins/registry.py`

The registry exposes helpers to:

- register a plugin
- register built-in plugins
- resolve a plugin by name
- list supported framework names

## Minimal plugin contract

A plugin is represented by:

- a `name`
- a `build_attack(entry, index, path) -> Attack` function

Conceptually:

```python
@dataclass(frozen=True)
class FrameworkPlugin:
    name: str
    build_attack: Callable[[dict[str, Any], int, Path], Attack]
```

## Built-in plugins

Current built-in plugin packages:

- `redteaming.plugins.pyrit`
- `redteaming.plugins.garak`

They currently return the framework-specific attack classes:

- `redteaming.plugins.pyrit.attack.PyritAttack`
- `redteaming.plugins.garak.attack.GarakAttack`

## What a plugin is expected to do

A framework plugin should:

- validate its attack-specific YAML fields
- reject invalid or misplaced fields early
- build a concrete `Attack` instance
- keep framework naming consistent with campaign YAML and reports

## Current runtime ownership

Framework-specific runtime logic currently lives under each plugin package and typically includes:

- attack class
- runner
- adapter (when needed)
- normalizer

## Design constraints

Plugin implementations should keep consistent:

- framework names exactly as exposed in YAML (`pyrit`, `garak`)
- attack semantics for existing framework modes
- normalized `AttackResult.framework` values
- clear separation between framework-specific logic and generic orchestration

## Extending the framework

To add a new framework plugin, the expected workflow is:

1. define a package under `src/redteaming/plugins/<framework_name>/`
2. implement `build_attack(...)`
3. create the runtime pieces needed by that framework
4. register the plugin in the registry
5. add attack examples and tests

## Recommended references

Useful files to read before adding a plugin:

- `src/redteaming/plugins/registry.py`
- `src/redteaming/plugins/pyrit/__init__.py`
- `src/redteaming/plugins/garak/__init__.py`
- `docs/campaign-spec.md`
- `docs/report-model.md`
