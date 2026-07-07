"""
镜牢基础设施层 — 旧单例适配器

Strangler Fig 的核心：包装 module.automation.auto 和 module.config.cfg
这两个全局单例，使其符合 mirror/domain/interfaces.py 的 Protocol 接口。

当新的 PerceptionBackend / ExecutorPort / ConfigPort 实现就绪时，
只需要更换这里的适配器（或直接注入新实现），领域代码零改动。

只读适配 — 不影响原有 globals 的行为。
"""
from __future__ import annotations

from typing import Any, Optional

from PIL import Image

from mirror.domain.interfaces import AutomationPort, ConfigPort


class LegacyAutomationAdapter:
    """包装 module.automation.auto 单例的适配器。

    所有方法/属性显式委托到旧实例，确保 Pyright 类型安全。
    """

    def __init__(self) -> None:
        from module.automation import auto as _old_auto

        self._old = _old_auto

    # ── 属性（Protocol 必需） ──
    @property
    def model(self) -> str:
        return self._old.model

    @model.setter
    def model(self, val: str) -> None:
        self._old.model = val

    @property
    def screenshot(self) -> Optional[Image.Image]:
        return self._old.screenshot

    # ── 截图 ──
    def take_screenshot(self, gray: bool = True) -> Optional[Image.Image]:
        return self._old.take_screenshot(gray)

    # ── 查找元素 ──
    def find_element(
        self,
        target: str,
        find_type: str = "image",
        threshold: float = 0.8,
        max_retries: int = 1,
        take_screenshot: bool = False,
        model: str | None = None,
        my_crop: tuple | None = None,
    ) -> list[float] | None:
        return self._old.find_element(
            target,
            find_type=find_type,
            threshold=threshold,
            max_retries=max_retries,
            take_screenshot=take_screenshot,
            model=model,
            my_crop=my_crop,
        )

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
        return self._old.click_element(
            target,
            find_type=find_type,
            threshold=threshold,
            max_retries=max_retries,
            take_screenshot=take_screenshot,
            offset=offset,
            action=action,
            times=times,
            dx=dx,
            dy=dy,
            model=model,
            my_crop=my_crop,
            click=click,
            drag_time=drag_time,
            interval=interval,
        )

    def find_text_element(
        self,
        target: list[str],
        my_crop: tuple | None = None,
        all_text: bool = False,
        only_text: bool = False,
        additional_stack: int = 0,
    ) -> Any:
        return self._old.find_text_element(
            target,
            my_crop=my_crop,
            all_text=all_text,
            only_text=only_text,
            additional_stack=additional_stack,
        )

    def find_language_text(
        self,
        target: str,
        my_crop: tuple | None = None,
        all_text: bool = False,
    ) -> str | None:
        # 原签名：find_language_text(target, zh_text, en_text, my_crop, all_text)
        return self._old.find_language_text(target, target, my_crop=my_crop, all_text=all_text)  # type: ignore[call-arg]

    # ── 鼠标操作 ──
    def mouse_to_blank(self) -> None:
        self._old.mouse_to_blank()

    def mouse_click(self, x: int, y: int, times: int = 1) -> None:
        self._old.mouse_click(x, y, times)

    def mouse_click_blank(self) -> None:
        self._old.mouse_click_blank()

    def mouse_drag(
        self,
        x: int,
        y: int,
        drag_time: float | None = None,
        dx: int = 0,
        dy: int = 0,
    ) -> None:
        self._old.mouse_drag(x, y, drag_time, dx, dy)

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
        return self._old.mouse_action_with_pos(
            coordinates,
            offset=offset,
            action=action,
            times=times,
            drag_time=drag_time,
            dx=dx,
            dy=dy,
            find_type=find_type,
            interval=interval,
        )

    # ── 键盘操作 ──
    def key_press(self, key: str) -> None:
        self._old.key_press(key)

    # ── 状态操作 ──
    def get_restore_time(self) -> float:
        return self._old.get_restore_time()

    def clear_img_cache(self) -> None:
        self._old.clear_img_cache()


class LegacyConfigAdapter:
    """包装 module.config.cfg 单例的适配器。"""

    def __init__(self) -> None:
        from module.config import cfg as _old_cfg

        self._old = _old_cfg

    # ── 窗口与缩放 ──
    @property
    def set_win_size(self) -> int:
        return self._old.set_win_size

    # ── 镜牢开关 ──
    @property
    def hard_mirror(self) -> bool:
        return self._old.hard_mirror

    @property
    def hard_mirror_single_bonuses(self) -> bool:
        return self._old.hard_mirror_single_bonuses

    @property
    def not_skip_whitegossypium(self) -> bool:
        return self._old.not_skip_whitegossypium

    @property
    def no_weekly_bonuses(self) -> bool:
        return self._old.no_weekly_bonuses

    @property
    def save_rewards(self) -> bool:
        return self._old.save_rewards

    @property
    def floor_3_exit(self) -> bool:
        return self._old.floor_3_exit

    # ── 通用配置 ──
    @property
    def background_click(self) -> bool:
        return self._old.background_click

    @property
    def mouse_action_interval(self) -> float:
        return self._old.mouse_action_interval

    def get_value(self, key: str, default: Any = None) -> Any:
        return self._old.get_value(key, default)


# ── 工厂函数（懒加载，避免 import 时创建） ──

_auto_adapter: LegacyAutomationAdapter | None = None
_cfg_adapter: LegacyConfigAdapter | None = None


def get_automation() -> AutomationPort:
    global _auto_adapter
    if _auto_adapter is None:
        _auto_adapter = LegacyAutomationAdapter()
    return _auto_adapter


def get_config() -> ConfigPort:
    global _cfg_adapter
    if _cfg_adapter is None:
        _cfg_adapter = LegacyConfigAdapter()
    return _cfg_adapter
