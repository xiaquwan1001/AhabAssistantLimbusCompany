"""
module2_executor — 执行层端口定义

从 AutomationPort 中提取所有执行相关方法，形成独立的 ExecutorPort 协议。
新模块只依赖此 Protocol，不依赖旧 Automation 单例。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ExecutorPort(Protocol):
    """执行操作接口 — 鼠标点击、拖拽、键盘输入。

    Lambdas: 见 module/automation/automation.py Automation 类中与执行相关的方法。
    本协议只声明 mirror/tasks/ 实际用到的执行方法。
    """

    # ── 鼠标操作 ──
    def mouse_to_blank(self) -> None: ...
    def mouse_click(self, x: int, y: int, times: int = 1) -> None: ...
    def mouse_click_blank(self) -> None: ...
    def mouse_drag(
        self,
        x: int,
        y: int,
        drag_time: float | None = None,
        dx: int = 0,
        dy: int = 0,
    ) -> None: ...
    def mouse_action_with_pos(
        self,
        coordinates: list[float],
        offset: bool = True,
        action: str = "click",
        times: int = 1,
        drag_time: float | None = None,
        dx: int = 0,
        dy: int = 0,
        find_type: str | None = None,
        interval: float = 0.5,
    ) -> bool: ...

    # ── 键盘操作 ──
    def key_press(self, key: str) -> None: ...

    # ── 菜单 / 状态操作 ──
    def get_restore_time(self) -> float: ...

    # ── 点击元素（查找+执行复合） ──
    def click_element(
        self,
        target: str,
        find_type: str = "image",
        threshold: float = 0.8,
        max_retries: int = 1,
        take_screenshot: bool = False,
        offset: bool = True,
        action: str = "click",
        times: int = 1,
        dx: int = 0,
        dy: int = 0,
        model: str | None = None,
        my_crop: tuple | None = None,
        click: bool = True,
        drag_time: float | None = None,
        interval: float = 0.5,
    ) -> bool | list[float]: ...
