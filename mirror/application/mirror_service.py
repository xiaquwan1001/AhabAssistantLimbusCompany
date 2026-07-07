"""
镜牢应用服务层 — Strangler Fig 编排

职责：
  1. 组装依赖（AutomationPort + ConfigPort + RunConfig）
  2. 实例化领域对象（MirrorStateMachine）
  3. 调用旧系统 Mirror.run() 完成实际工作
  4. 逐步吸收旧业务逻辑，最终替代 tasks 层

当前状态（Strangler Fig Phase 1）：
  完全委托给旧的 tasks/mirror/mirror.py Mirror 类。
  未来 Phase 2-N 将逐步把具体 handler 从旧的 Mirror 迁移到此文件。
"""
from __future__ import annotations

from typing import Optional

from mirror.domain.interfaces import AutomationPort, ConfigPort, RunConfig
from mirror.domain.state_machine import MirrorStateMachine
from mirror.infra.legacy_adapters import get_automation, get_config


class MirrorService:
    """镜牢运行服务 — 依赖注入入口点。"""

    def __init__(
        self,
        automation: Optional[AutomationPort] = None,
        config: Optional[ConfigPort] = None,
    ):
        self.auto = automation or get_automation()
        self.config = config or get_config()

    # ── Strangler Fig Phase 1: 全权委托给旧 Mirror ──

    def run_mirror(self, run_config: RunConfig) -> bool:
        """执行一次完整镜牢。

        最终目标：此方法逐步吸收 Mirror.run() 的调度链。
        当前实现：构造旧 Mirror 实例 + 委托。
        """
        from module.config import TeamSetting

        # 构造 TeamSetting
        ts = TeamSetting()
        for field_name, value in run_config.__dict__.items():
            if hasattr(ts, field_name):
                setattr(ts, field_name, value)

        # 兼容旧 Mirror 的 hard_mode 字段
        ts.hard_mirror = run_config.hard_mode

        # 委托旧系统
        from tasks.mirror.mirror import Mirror as OldMirror

        old_mirror = OldMirror(ts, run_config.team_order, automation=self.auto, config=self.config)
        return old_mirror.run()

    # ── Strangler Fig Phase 2+: 逐步迁移的 handler ──

    def prepare_and_enter(self, run_config: RunConfig) -> bool:
        """road_to_mir + 楼层识别 — 未来从旧 Mirror 迁移至此。"""
        # TODO(strangler): 逐步从 Mirror.road_to_mir() 迁移
        sm = MirrorStateMachine(
            loop_count=250,
            floor_3_exit=run_config.floor_3_exit,
        )
        sm.phase = "entering"
        return True
