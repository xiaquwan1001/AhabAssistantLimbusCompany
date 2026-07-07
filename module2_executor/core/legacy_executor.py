"""
module2_executor/core/legacy_executor.py — 旧版 Automation 适配器

将 module.automation.auto 单例包装为 ExecutorPort 协议实现。
所有方法直接委托给旧的 auto 对象，不做额外逻辑。
"""

from __future__ import annotations

from typing import Optional

from module2_executor.core.executor_port import ExecutorPort


def _get_auto():
    """延迟导入旧的 auto 单例，避免模块初始化时的循环依赖。"""
    from module.automation import auto

    return auto


class LegacyExecutor:
    """将旧版 Automation 单例包装为 ExecutorPort 协议。"""

    # ── 鼠标操作 ──

    def mouse_to_blank(self) -> None:
        _get_auto().mouse_to_blank()

    def mouse_click(self, x: int, y: int, times: int = 1) -> None:
        _get_auto().mouse_click(x, y, times)

    def mouse_click_blank(self) -> None:
        _get_auto().mouse_click_blank()

    def mouse_drag(
        self,
        x: int,
        y: int,
        drag_time: float | None = None,
        dx: int = 0,
        dy: int = 0,
    ) -> None:
        _get_auto().mouse_drag(x, y, drag_time, dx, dy)

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
    ) -> bool:
        return _get_auto().mouse_action_with_pos(
            coordinates,
            offset,
            action,
            times,
            drag_time,
            dx,
            dy,
            find_type,
            interval,
        )

    # ── 键盘操作 ──

    def key_press(self, key: str) -> None:
        _get_auto().key_press(key)

    # ── 菜单 / 状态操作 ──

    def get_restore_time(self) -> float:
        return _get_auto().get_restore_time()

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
    ) -> bool | list[float]:
        return _get_auto().click_element(
            target,
            find_type,
            threshold,
            max_retries,
            take_screenshot,
            offset,
            action,
            times,
            dx,
            dy,
            model,
            my_crop,
            click,
            drag_time,
            interval,
        )
