"""
module3_perception — 旧 auto 单例适配器

包装 module.automation.auto 单例以符合 PerceptionPort 协议。
懒加载导入，避免模块级 auto 依赖。

只读适配 — 不影响原有 globals 的行为。
"""

from __future__ import annotations

from typing import Any, Optional

from PIL import Image

from module3_perception.core.perception_port import PerceptionPort


def _get_auto():
    """懒加载旧 auto 单例。"""
    from module.automation import auto

    return auto


class LegacyPerceptionAdapter:
    """包装 module.automation.auto 单例的感知适配器。

    将旧 auto 实例的感知方法委托给 PerceptionPort 协议。
    所有方法/属性显式委托到旧实例，确保 Pyright 类型安全。
    """

    # ── 配置属性 ──

    @property
    def model(self) -> str:
        return _get_auto().model

    @model.setter
    def model(self, val: str) -> None:
        _get_auto().model = val

    # ── 截图 ──

    @property
    def screenshot(self) -> Optional[Image.Image]:
        return _get_auto().screenshot

    def take_screenshot(self, gray: bool = True) -> Optional[Image.Image]:
        return _get_auto().take_screenshot(gray)

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
        return _get_auto().find_element(
            target,
            find_type=find_type,
            threshold=threshold,
            max_retries=max_retries,
            take_screenshot=take_screenshot,
            model=model,
            my_crop=my_crop,
        )

    def find_text_element(
        self,
        target: list[str],
        my_crop: tuple | None = None,
        all_text: bool = False,
        only_text: bool = False,
        additional_stack: int = 0,
    ) -> Any:
        return _get_auto().find_text_element(
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
        # PerceptionPort 简化了协议：只传 target（对应旧 API 的 zh_text 位置）
        return _get_auto().find_language_text(
            target, target, my_crop=my_crop, all_text=all_text
        )  # type: ignore[call-arg]

    # ── 缓存管理 ──

    def clear_img_cache(self) -> None:
        _get_auto().clear_img_cache()


# ── 工厂函数（懒加载单例） ──

_adapter: LegacyPerceptionAdapter | None = None


def get_perception() -> PerceptionPort:
    """获取 LegacyPerceptionAdapter 单例，返回 PerceptionPort 协议类型。"""
    global _adapter
    if _adapter is None:
        _adapter = LegacyPerceptionAdapter()
    return _adapter
