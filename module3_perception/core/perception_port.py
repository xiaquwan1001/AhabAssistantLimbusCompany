"""
module3_perception — 感知层端口定义

从 AutomationPort 中提取所有感知相关方法，形成独立的 PerceptionPort 协议。
新模块只依赖此 Protocol，不依赖旧 Automation 单例。
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from PIL import Image


@runtime_checkable
class PerceptionPort(Protocol):
    """感知操作接口 — 截图、模板匹配、OCR。

    Lambdas: 见 module/automation/automation.py Automation 类中与感知相关的方法。
    本协议只声明 mirror/tasks/ 实际用到的感知方法。
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

    # ── 缓存管理 ──
    def clear_img_cache(self) -> None: ...
