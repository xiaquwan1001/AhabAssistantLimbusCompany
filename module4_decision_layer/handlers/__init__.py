"""
module4_decision_layer/handlers — 决策层处理器

每个 handler 封装一个游戏操作逻辑，接收注入的 AutomationPort，
返回 bool 表示是否执行了操作（供调度器决定 continue/break）。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class GameHandler(Protocol):
    def __call__(self, auto: Any) -> bool:
        """执行操作。返回 True 表示执行了动作（调度器应 continue）。"""
        ...
