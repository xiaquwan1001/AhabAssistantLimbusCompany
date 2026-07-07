"""
Source of truth for mirror state — migrated from mirror/domain/state_machine.py.

镜牢状态机 — 纯状态流转，不依赖 module.automation / module.config

职责：
  跟踪镜牢当前阶段、楼层、主循环计数器。
  不执行任何自动化操作，只回答"当前状态是什么"。

使用方式：
  sm = MirrorStateMachine(loop_count=250, floor_3_exit=False)
  while not sm.is_done:
      ...
      sm.on_loop_tick()
      if sm.should_exit_early(): ...
      if sm.should_switch_to_normal(): ...
      if sm.should_switch_to_aggressive(): ...
      if sm.main_loop_count < 0: sm.on_back_to_menu()
"""

from enum import Enum


class MirrorPhase(Enum):
    """镜牢高层阶段。"""
    ENTERING = "entering"
    NAVIGATING = "navigating"
    IN_NODE = "in_node"
    REWARD = "reward"
    STATS = "stats"
    DONE = "done"


class MirrorStateMachine:
    """镜牢状态机 — 跟踪阶段、楼层、主循环计数器。"""

    def __init__(self, loop_count: int = 250, floor_3_exit: bool = False):
        self.phase: MirrorPhase = MirrorPhase.ENTERING
        self.floor: int = 0
        self.main_loop_count: int = loop_count
        self.back_menu_count: int = 0
        self.floor_3_exit: bool = floor_3_exit

    @property
    def is_done(self) -> bool:
        return self.phase == MirrorPhase.DONE

    def should_exit_early(self) -> bool:
        return self.floor_3_exit and self.floor >= 4

    def on_floor_changed(self, new_floor: int):
        self.floor = new_floor
        self.phase = MirrorPhase.NAVIGATING

    def on_loop_tick(self):
        self.main_loop_count -= 1

    def should_switch_to_aggressive(self) -> bool:
        return self.main_loop_count < 15

    def should_switch_to_normal(self) -> bool:
        return self.main_loop_count < 75

    def on_back_to_menu(self):
        self.back_menu_count += 1
        self.main_loop_count = 250
