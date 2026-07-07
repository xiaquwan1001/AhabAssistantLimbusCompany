"""镜牢基础设施层 — 旧系统适配器与新模块入口。"""

from mirror.infra.legacy_adapters import (
    LegacyAutomationAdapter,
    LegacyConfigAdapter,
    get_automation,
    get_config,
)

__all__ = [
    "LegacyAutomationAdapter",
    "LegacyConfigAdapter",
    "get_automation",
    "get_config",
]
