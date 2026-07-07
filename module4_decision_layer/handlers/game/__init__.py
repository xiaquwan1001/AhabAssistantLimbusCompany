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


class EgoGiftConfirmHandler:
    """确认获取EGO饰品。

    对应旧 Mirror._run_ego_gift_confirm()
    """

    def __init__(self, auto: Optional[AutomationPort] = None):
        self.auto = auto

    def __call__(self, auto: Optional[AutomationPort] = None) -> bool:
        a = auto or self.auto
        if a is None:
            raise ValueError("EgoGiftConfirmHandler requires 'auto' (AutomationPort)")
        return bool(a.click_element("mirror/road_in_mir/ego_gift_get_confirm_assets.png"))


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


class EnterNodeHandler:
    """进入寻路线路节点。

    对应旧 Mirror._run_enter_node()
    """

    def __init__(self, auto: Optional[AutomationPort] = None):
        self.auto = auto

    def __call__(self, auto: Optional[AutomationPort] = None) -> bool:
        a = auto or self.auto
        if a is None:
            raise ValueError("EnterNodeHandler requires 'auto' (AutomationPort)")
        return bool(a.click_element("mirror/road_in_mir/enter_assets.png"))


class EventHandler:
    """处理事件跳过。

    对应旧 Mirror._run_event()
    """

    def __init__(self, auto: Optional[AutomationPort] = None):
        self.auto = auto

    def __call__(self, auto: Optional[AutomationPort] = None) -> bool:
        a = auto or self.auto
        if a is None:
            raise ValueError("EventHandler requires 'auto' (AutomationPort)")
        from module4_decision_layer.core.constants import EVENT_CLICK_TIMES

        if not a.click_element("event/skip_assets.png", times=EVENT_CLICK_TIMES):
            return False
        return True


class EventEffectHandler:
    """处理选择增益事件（少见）。

    对应旧 Mirror._run_event_effect()
    """

    def __init__(self, auto: Optional[AutomationPort] = None):
        self.auto = auto

    def __call__(self, auto: Optional[AutomationPort] = None) -> bool:
        a = auto or self.auto
        if a is None:
            raise ValueError("EventEffectHandler requires 'auto' (AutomationPort)")
        if not a.click_element(
            "mirror/road_in_mir/event_effect_button.png", threshold=0.75
        ):
            return False
        a.click_element("mirror/road_in_mir/select_event_effect_confirm.png")
        return True


class NoTeamHandler:
    """没有配队时重置。

    对应旧 Mirror._run_no_team()
    """

    def __init__(self, auto: Optional[AutomationPort] = None):
        self.auto = auto

    def __call__(self, auto: Optional[AutomationPort] = None) -> bool:
        a = auto or self.auto
        if a is None:
            raise ValueError("NoTeamHandler requires 'auto' (AutomationPort)")
        if not a.find_element("battle/select_none_assets.png"):
            return False
        a.mouse_click_blank()
        return True


class RewardCardHandler:
    """选择奖励卡牌。

    对应旧 Mirror._run_reward_card()
    """

    def __init__(
        self,
        auto: Optional[AutomationPort] = None,
        reward_cards_select: Optional[int] = None,
    ):
        self.auto = auto
        self.reward_cards_select = reward_cards_select

    def __call__(self, auto: Optional[AutomationPort] = None) -> bool:
        a = auto or self.auto
        if a is None:
            raise ValueError("RewardCardHandler requires 'auto' (AutomationPort)")
        if not a.find_element("mirror/road_in_mir/select_encounter_reward_card_assets.png"):
            return False
        from tasks.mirror.reward_card import get_reward_card

        if self.reward_cards_select:
            get_reward_card(self.reward_cards_select)
        else:
            get_reward_card()
        return True
