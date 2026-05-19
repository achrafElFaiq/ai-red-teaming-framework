from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from redteaming.domain.models.attack import Attack


AttackBuilder = Callable[[dict[str, Any], int, Path], Attack]


@dataclass(frozen=True)
class FrameworkPlugin:
    name: str
    build_attack: AttackBuilder


_PLUGINS: dict[str, FrameworkPlugin] = {}
_BUILTINS_REGISTERED = False


def register_plugin(plugin: FrameworkPlugin) -> None:
    _PLUGINS[plugin.name] = plugin


def register_builtin_plugins() -> None:
    global _BUILTINS_REGISTERED
    if _BUILTINS_REGISTERED:
        return

    from .garak import GARAK_PLUGIN
    from .pyrit import PYRIT_PLUGIN

    register_plugin(PYRIT_PLUGIN)
    register_plugin(GARAK_PLUGIN)
    _BUILTINS_REGISTERED = True


def get_plugin(name: str) -> FrameworkPlugin:
    register_builtin_plugins()
    return _PLUGINS[name]


def list_framework_names() -> list[str]:
    register_builtin_plugins()
    return sorted(_PLUGINS)


