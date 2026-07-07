"""
Strangled re-exports — adapters live in mirror/infra/legacy_adapters.py.

Usage:
    from module4_decision_layer.adapters import get_automation, get_config
"""

from mirror.infra.legacy_adapters import get_automation, get_config

__all__ = [
    "get_automation",
    "get_config",
]
