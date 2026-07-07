"""
镜牢领域层 — 端口（接口）定义

Strangler Fig 的第一步：定义核心依赖的抽象接口。
AutomationPort 与 ConfigPort 完全独立于 module.automation / module.config，
新代码只依赖这些 Protocol，不依赖任何全局单例。

Source of truth: migrated from mirror/domain/interfaces.py

后续适配器（mirror/infra/legacy_adapters.py）包装旧单例实现这些接口，
当新模块（module3_perception / module2_executor / module4_decision_layer）就绪时，
只需换掉适配器即可 — 领域代码零改动。
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from PIL import Image

__all__ = [
    "AutomationPort",
    "ConfigPort",
    "RunConfig",
]


# ── 自动化端口 ──────────────────────────────────────────────


@runtime_checkable
class AutomationPort(Protocol):
    """自动化操作接口 — 截图、点击、查找元素、OCR、按键。

    Lambdas: 见 module/automation/automation.py Automation 类。
    本协议只声明 mirror/tasks/ 实际用到的方法，不追求完整覆盖。
    """

    # ── 配置属性 ──
    model: str  # 当前识别模型（"clam" / "normal"）

    # ── 截图 ──
    def take_screenshot(self, gray: bool = True) -> Image.Image | None: ...
    @property
    def screenshot(self) -> Image.Image | None: ...

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
    ) -> list[float] | None: ...

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

    def find_text_element(
        self,
        target: list[str],
        my_crop: tuple | None = None,
        all_text: bool = False,
        only_text: bool = False,
        additional_stack: int = 0,
    ) -> Any: ...

    def find_language_text(
        self,
        target: str,
        my_crop: tuple | None = None,
        all_text: bool = False,
    ) -> str | None: ...

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
    def clear_img_cache(self) -> None: ...


# ── 配置端口 ──────────────────────────────────────────────


@runtime_checkable
class ConfigPort(Protocol):
    """游戏配置接口 — 只读配置项。

    Lambdas: 见 module/config/config.py Config 类。
    本协议只声明 mirror/tasks/ 实际用到的配置属性/方法。
    """

    # ── 窗口与缩放 ──
    @property
    def set_win_size(self) -> int: ...

    # ── 镜牢开关（只读） ──
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

    # ── 通用配置（只读） ──
    @property
    def background_click(self) -> bool: ...
    @property
    def mouse_action_interval(self) -> float: ...

    # ── 通用配置访问 ──
    def get_value(self, key: str, default: Any = None) -> Any: ...


# ── 重构辅助：运行配置 — 纯净数据类 ────────────────────


from dataclasses import dataclass, field
from typing import List


@dataclass
class RunConfig:
    """一次镜牢运行的所有配置参数（纯数据）。

    从 TeamSetting + cfg 抽取，经 Mirror.__init__ 构造后注入各 handler。
    所有属性都是值类型或简单容器，不含任意对象引用。
    """

    # ── 队伍配置 ──
    team_order: int = 0
    sinner_order: List[int] = field(default_factory=lambda: [0] * 12)
    team_number: int = 1
    team_system: int = 0
    second_system: int = 0
    second_system_select: int = 0
    second_system_setting: int = 0

    # ── 行为开关 ──
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

    # ── 饰品策略 ──
    opening_bonus: int = 0
    opening_items: int = 0
    opening_items_select: int = 0
    opening_items_system: int = 0
    use_custom_theme_pack_weight: bool = False
    reward_cards: int = 0
    reward_cards_select: int = 0

    # ── 观测 ├EGO 饰品 ──
    observe_ego_gift: bool = False
    observe_ego_gift_selected: List[int] = field(default_factory=list)
