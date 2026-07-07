"""镜牢领域层 — 纯净业务逻辑，零外部依赖。"""

from mirror.domain.interfaces import AutomationPort, ConfigPort, RunConfig
from mirror.domain.state_machine import MirrorPhase, MirrorStateMachine

# 向后兼容：旧 import 路径仍然可用
from mirror.domain.constants import (
    MIRROR_MAIN_LOOP,
    DEFAULT_LOOP,
    SHORT_LOOP,
    MIN_LOOP,
    SINNER_LIVE_THRESHOLD,
    BATTLE_FAIL_RETRY_THRESHOLD,
    EVENT_CLICK_TIMES,
    BLANK_CLICK_TIMES,
    get_scale,
)

__all__ = [
    "AutomationPort",
    "ConfigPort",
    "RunConfig",
    "MirrorPhase",
    "MirrorStateMachine",
    "MIRROR_MAIN_LOOP",
    "DEFAULT_LOOP",
    "SHORT_LOOP",
    "MIN_LOOP",
    "SINNER_LIVE_THRESHOLD",
    "BATTLE_FAIL_RETRY_THRESHOLD",
    "EVENT_CLICK_TIMES",
    "BLANK_CLICK_TIMES",
    "get_scale",
]
