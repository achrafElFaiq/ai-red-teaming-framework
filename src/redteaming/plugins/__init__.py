"""Plugin registry and built-in framework plugins."""

from .registry import (
    FrameworkPlugin,
    get_plugin,
    list_framework_names,
    register_builtin_plugins,
    register_plugin,
)

__all__ = [
    "FrameworkPlugin",
    "get_plugin",
    "list_framework_names",
    "register_builtin_plugins",
    "register_plugin",
]


