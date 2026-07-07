"""镜牢模块 — Strangler Fig 重构入口

领域层 (domain/) — 纯净业务逻辑，零外部依赖。
基础设施层 (infra/) — 包装旧单例，适配新接口。
应用服务层 (application/) — 组装依赖，编排流程。

使用方式：
    from mirror import MirrorService
    from mirror.domain import RunConfig

    service = MirrorService()
    service.run_mirror(RunConfig(team_order=1, hard_mode=True))
"""

from mirror.application.mirror_service import MirrorService
from mirror.domain.interfaces import RunConfig
from mirror.infra.legacy_adapters import get_automation, get_config

__all__ = [
    "MirrorService",
    "RunConfig",
    "get_automation",
    "get_config",
]
