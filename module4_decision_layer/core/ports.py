"""
module4_decision_layer/core — 端口定义与组合自动化

源真文件。所有新代码从 module4_decision_layer 导入。
旧路径 mirror/domain/interfaces.py → strangled re-export。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol, runtime_checkable

from PIL import Image


# ════════════════════════════════════════════════════════════════
# 自动化端口 — 保持向后兼容
# ════════════════════════════════════════════════════════════════


@runtime_checkable
class AutomationPort(Protocol):
    """自动化操作接口 — 截图、点击、查找元素、OCR、按键。

    向后兼容协议。新代码应依赖 PerceptionPort + ExecutorPort + ConfigPort。
    """

    model: str

    def take_screenshot(self, gray: bool = True) -> Image.Image | None: ...
    @property
    def screenshot(self) -> Image.Image | None: ...

    def find_element(self, target: str, **kwargs) -> list[float] | None: ...
    def click_element(self, target: str, **kwargs) -> bool | list[float]: ...
    def find_text_element(self, target: list[str], **kwargs) -> Any: ...
    def find_language_text(self, target: str, **kwargs) -> str | None: ...

    def mouse_to_blank(self) -> None: ...
    def mouse_click(self, x: int, y: int, times: int = 1) -> None: ...
    def mouse_click_blank(self) -> None: ...
    def mouse_drag(self, x: int, y: int, **kwargs) -> None: ...
    def mouse_action_with_pos(self, coordinates: list[float], **kwargs) -> bool: ...
    def key_press(self, key: str) -> None: ...
    def get_restore_time(self) -> float: ...
    def clear_img_cache(self) -> None: ...


# ════════════════════════════════════════════════════════════════
# 配置端口
# ════════════════════════════════════════════════════════════════


@runtime_checkable
class ConfigPort(Protocol):
    @property
    def set_win_size(self) -> int: ...
    @property
    def hard_mirror(self) -> bool: ...
    @property
    def hard_mirror_single_bonuses(self) -> bool: ...
    @property
    def not_skip_whitegossypium(self) -> bool: ...
    @property
    def no_weekly_bonuses(self) -> bool: ...
    @property
    def save_rewards(self) -> bool: ...
    @property
    def floor_3_exit(self) -> bool: ...
    @property
    def background_click(self) -> bool: ...
    @property
    def mouse_action_interval(self) -> float: ...
    def get_value(self, key: str, default: Any = None) -> Any: ...


# ════════════════════════════════════════════════════════════════
# 运行参数 — 纯数据类
# ════════════════════════════════════════════════════════════════


@dataclass
class RunConfig:
    team_order: int = 0
    sinner_order: List[int] = field(default_factory=lambda: [0] * 12)
    team_number: int = 1
    team_system: int = 0
    second_system: int = 0
    second_system_select: int = 0
    second_system_setting: int = 0
    hard_mode: bool = False
    hard_mirror_single_bonuses: bool = False
    floor_3_exit: bool = False
    not_skip_whitegossypium: bool = False
    no_weekly_bonuses: bool = False
    save_rewards: bool = False
    avoid_skill_3: bool = False
    re_formation_each_floor: bool = False
    defense_first_round: bool = False
    use_starlight: bool = False
    opening_bonus: int = 0
    opening_items: int = 0
    opening_items_select: int = 0
    opening_items_system: int = 0
    use_custom_theme_pack_weight: bool = False
    reward_cards: int = 0
    reward_cards_select: int = 0
    observe_ego_gift: bool = False
    observe_ego_gift_selected: List[int] = field(default_factory=list)


# ════════════════════════════════════════════════════════════════
# 组合自动化 — 由 PerceptionPort + ExecutorPort 构成
# ════════════════════════════════════════════════════════════════


class ComposedAutomation:
    """用独立的 PerceptionPort + ExecutorPort 组合实现 AutomationPort。

    当各层已有原生实现（而非包装老 auto 单例时），用此组合替代
    LegacyAutomationAdapter，实现真正的架构解耦。
    """

    def __init__(
        self,
        perception: "Any",  # PerceptionPort (forward ref to avoid circular)
        executor: "Any",  # ExecutorPort
        config: "Any | None" = None,  # ConfigPort
    ):
        self._p = perception
        self._e = executor
        self._c = config

    # ── 感知相关（委托到 _p）──
    @property
    def model(self) -> str:
        return getattr(self._p, "model", "clam")

    @model.setter
    def model(self, val: str) -> None:
        if hasattr(self._p, "model"):
            self._p.model = val

    @property
    def screenshot(self) -> Image.Image | None:
        return getattr(self._p, "screenshot", None)

    def take_screenshot(self, gray: bool = True) -> Image.Image | None:
        return self._p.take_screenshot(gray)

    def find_element(self, target: str, **kwargs) -> list[float] | None:
        return self._p.find_element(target, **kwargs)

    def find_text_element(self, target: list[str], **kwargs) -> Any:
        return self._p.find_text_element(target, **kwargs)

    def find_language_text(self, target: str, **kwargs) -> str | None:
        return self._p.find_language_text(target, **kwargs)

    def clear_img_cache(self) -> None:
        self._p.clear_img_cache()

    # ── 执行相关（委托到 _e）──
    def click_element(self, target: str, **kwargs) -> bool | list[float]:
        return self._e.click_element(target, **kwargs)

    def mouse_to_blank(self) -> None:
        self._e.mouse_to_blank()

    def mouse_click(self, x: int, y: int, times: int = 1) -> None:
        self._e.mouse_click(x, y, times)

    def mouse_click_blank(self) -> None:
        self._e.mouse_click_blank()

    def mouse_drag(self, x: int, y: int, **kwargs) -> None:
        self._e.mouse_drag(x, y, **kwargs)

    def mouse_action_with_pos(self, coordinates: list[float], **kwargs) -> bool:
        return self._e.mouse_action_with_pos(coordinates, **kwargs)

    def key_press(self, key: str) -> None:
        self._e.key_press(key)

    def get_restore_time(self) -> float:
        return self._e.get_restore_time()


__all__ = [
    "AutomationPort",
    "ConfigPort",
    "RunConfig",
    "ComposedAutomation",
]
