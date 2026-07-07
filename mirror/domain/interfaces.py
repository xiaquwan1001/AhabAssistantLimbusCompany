"""
镜牢领域层 — 端口定义（已迁移至 module4_decision_layer）

Strangler — source of truth moved to module4_decision_layer/core/ports.py.
保留此文件仅用于向后兼容，新 import 应从 module4_decision_layer 导入。
"""
from module4_decision_layer.core.ports import (
    AutomationPort,
    ConfigPort,
    RunConfig,
    ComposedAutomation,
)

__all__ = [
    "AutomationPort",
    "ConfigPort",
    "RunConfig",
    "ComposedAutomation",
]
