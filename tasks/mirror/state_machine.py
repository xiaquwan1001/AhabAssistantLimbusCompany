"""
镜牢状态机 — 纯状态流转，不依赖 module.automation / module.config

职责：
  跟踪镜牢当前处于哪个阶段，以及下一阶段应该是什么。
  不执行任何自动化操作，只回答"下一步该做什么"。

使用方式：
  state_machine = MirrorStateMachine()
  while not state_machine.is_done:
      action = state_machine.get_next_action()
      # Mirror 类根据 action 执行对应操作
      state_machine.on_action_complete(action, context)
"""

from enum import Enum
from typing import Optional


class MirrorAction(Enum):
    """镜牢主循环可执行的动作（按优先级排序）。"""
    FLOOR_EXIT_CHECK = "floor_exit_check"
    CLAIM_REWARD_CHECK = "claim_reward_check"
    THEME_PACK = "theme_pack"
    EVENT_EFFECT = "event_effect"
    ROAD_NAVIGATION = "road_navigation"
    ENTER_NODE = "enter_node"
    TEAM_SELECT = "team_select"
    BATTLE_FAIL_CHECK = "battle_fail_check"
    BATTLE_DEPLOY = "battle_deploy"
    NO_TEAM = "no_team"
    BATTLE = "battle"
    STARLIGHT = "starlight"
    EGO_GIFT = "ego_gift"
    EGO_GIFT_CONFIRM = "ego_gift_confirm"
    EVENT = "event"
    SHOP = "shop"
    REWARD_CARD = "reward_card"
    ENTER_MIRROR = "enter_mirror"
    INIT_EGO_GIFT = "init_ego_gift"
    OBSERVE_EGO_GIFT = "observe_ego_gift"
    CLOSE_INFINITY = "close_infinity"
    DISMISS_PROMPT = "dismiss_prompt"
    ANTI_STUCK = "anti_stuck"


class MirrorPhase(Enum):
    """镜牢高层阶段。"""
    ENTERING = "entering"           # 进入镜牢
    NAVIGATING = "navigating"       # 寻路中
    IN_NODE = "in_node"            # 在节点中（战斗/商店/事件）
    REWARD = "reward"              # 领取奖励
    STATS = "stats"               # 统计输出
    DONE = "done"                 # 完成


class MirrorStateMachine:
    """镜牢状态机 — 跟踪阶段、楼层、主循环计数器。"""

    def __init__(self, loop_count: int = 250, floor_3_exit: bool = False):
        self.phase: MirrorPhase = MirrorPhase.ENTERING
        self.floor: int = 0
        self.main_loop_count: int = loop_count
        self.back_menu_count: int = 0
        self.floor_3_exit: bool = floor_3_exit
        self._action_index: int = 0
        self._prioritized_actions: list[MirrorAction] = list(MirrorAction)

    @property
    def is_done(self) -> bool:
        return self.phase == MirrorPhase.DONE

    def should_exit_early(self) -> bool:
        """如果启用了 floor_3_exit 且已到第4层，应退出。"""
        return self.floor_3_exit and self.floor >= 4

    def get_next_action(self) -> MirrorAction:
        """返回当前优先级最高的待检测动作。"""
        if self.main_loop_count >= 50:
            return self._prioritized_actions[self._action_index]

        # 主循环计数低时跳过非关键动作
        if self.main_loop_count < 50:
            # 只保留核心检测
            core = [
                MirrorAction.FLOOR_EXIT_CHECK,
                MirrorAction.CLAIM_REWARD_CHECK,
                MirrorAction.THEME_PACK,
                MirrorAction.ROAD_NAVIGATION,
                MirrorAction.ENTER_NODE,
                MirrorAction.BATTLE_DEPLOY,
                MirrorAction.BATTLE,
                MirrorAction.SHOP,
                MirrorAction.EVENT,
                MirrorAction.ANTI_STUCK,
            ]
            return core[self._action_index] if self._action_index < len(core) else MirrorAction.ANTI_STUCK

        return self._prioritized_actions[self._action_index]

    def on_floor_changed(self, new_floor: int):
        """楼层变化时更新状态。"""
        self.floor = new_floor
        self.phase = MirrorPhase.NAVIGATING

    def on_theme_pack_selected(self):
        """主题包选择后给主循环加 bonus 次数。"""
        self.main_loop_count += 50

    def on_action_complete(self, action: MirrorAction, matched: bool):
        """动作执行完毕后更新状态机内部计数。"""
        if not matched:
            self._action_index += 1
        else:
            self._action_index = 0
            # 部分动作影响主循环计数
            if action in (MirrorAction.THEME_PACK,):
                self.main_loop_count += 50

    def on_loop_tick(self):
        """主循环每 tick 调用一次（防卡死逻辑）。"""
        self.main_loop_count -= 1

    def should_switch_to_aggressive(self) -> bool:
        """主循环计数低时切换到激进模式。"""
        return self.main_loop_count < 15

    def should_switch_to_normal(self) -> bool:
        return self.main_loop_count < 75

    def on_back_to_menu(self):
        """返回主界面时重置状态。"""
        self.back_menu_count += 1
        self.main_loop_count = 250
        self._action_index = 0
