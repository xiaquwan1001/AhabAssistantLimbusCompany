"""镜牢领域层 — 纯净业务逻辑，零外部依赖。

Strangled — source of truth moved to module4_decision_layer/core/.
"""

# Strangled — source of truth moved to module4_decision_layer
from module4_decision_layer.core.ports import AutomationPort, ConfigPort, RunConfig
from module4_decision_layer.core.state import MirrorPhase, MirrorStateMachine
from module4_decision_layer.core.constants import (
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
