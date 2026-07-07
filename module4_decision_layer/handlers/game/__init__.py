"""
game/ — 镜牢游戏操作 handler

从旧 Mirror._run_* 方法逐步迁移至此。
每个 handler 接收注入的 AutomationPort，纯逻辑，零全局依赖。
"""

from __future__ import annotations

from typing import Any, Optional

from module4_decision_layer.core.ports import AutomationPort


class DismissPromptHandler:
    """关闭首屏提示。

    对应旧 Mirror._run_dismiss_prompt()
    """

    def __init__(self, auto: Optional[AutomationPort] = None):
        self.auto = auto

    def __call__(self, auto: Optional[AutomationPort] = None) -> bool:
        a = auto or self.auto
        if a is None:
            raise ValueError("DismissPromptHandler requires 'auto' (AutomationPort)")
        if not (
            a.find_element("home/first_prompt_assets.png", model="clam")
            and a.find_element("home/back_assets.png", model="normal")
        ):
            return False
        a.click_element("home/back_assets.png")
        return True


class CloseInfinityHandler:
    """关闭无限镜牢弹窗。

    对应旧 Mirror._run_close_infinity()
    """

    def __init__(self, auto: Optional[AutomationPort] = None):
        self.auto = auto

    def __call__(self, auto: Optional[AutomationPort] = None) -> bool:
        a = auto or self.auto
        if a is None:
            raise ValueError("CloseInfinityHandler requires 'auto' (AutomationPort)")
        if not a.find_element("mirror/infinity_mirror_assets.png"):
            return False
        a.click_element("mirror/infinity_mirror_close_assets.png")
        return True
