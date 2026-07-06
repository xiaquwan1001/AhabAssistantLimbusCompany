"""
图像差异计算工具 - 检测画面跳变替代固定 sleep

提供基于 OpenCV absdiff 的画面变化检测，适用于：
- 等待加载动画结束（画面从变动→稳定）
- 等待按钮/弹窗出现（画面从A→B）
- 替代固定 sleep() 的保守等待

依赖：numpy, cv2（均为 AALC 已有依赖，比 PIL ImageChops 快 5-10x）
"""

import time
from typing import Optional, Callable

import cv2
import numpy as np
from PIL import Image


class ImageDiff:
    """图像差异计算工具（基于 OpenCV absdiff）"""

    @staticmethod
    def _to_array(img: Image.Image) -> np.ndarray:
        """PIL Image → numpy ndarray（不拷贝，零开销）"""
        return np.array(img)

    @staticmethod
    def calculate_diff_ratio(img1: Image.Image, img2: Image.Image) -> float:
        """
        计算两张图像的差异度（0~1）

        :param img1: 第一张图像
        :param img2: 第二张图像
        :return: 差异度，0表示完全相同，1表示完全不同
        """
        arr1 = ImageDiff._to_array(img1)
        arr2 = ImageDiff._to_array(img2)

        if arr1.shape != arr2.shape:
            h, w = arr1.shape[:2]
            arr2 = cv2.resize(arr2, (w, h), interpolation=cv2.INTER_AREA)

        # 统一转灰度（单通道时保留原值）
        if arr1.ndim == 3:
            arr1 = cv2.cvtColor(arr1, cv2.COLOR_RGB2GRAY)
        if arr2.ndim == 3:
            arr2 = cv2.cvtColor(arr2, cv2.COLOR_RGB2GRAY)

        diff = cv2.absdiff(arr1, arr2)
        return float(np.mean(diff) / 255.0)

    @staticmethod
    def is_significant_change(
        img1: Image.Image, img2: Image.Image, threshold: float = 0.05
    ) -> bool:
        """
        判断两张图像是否有显著变化

        :param img1: 第一张图像
        :param img2: 第二张图像
        :param threshold: 变化阈值（0~1），默认 5%
        :return: True 表示有显著变化
        """
        return ImageDiff.calculate_diff_ratio(img1, img2) >= threshold

    @staticmethod
    def quick_hash(image: Image.Image) -> int:
        """
        计算图像快速感知哈希（用于快速排除相同画面）

        :param image: 输入图像
        :return: 64位感知哈希整数
        """
        arr = ImageDiff._to_array(image)
        small = cv2.resize(arr, (8, 8), interpolation=cv2.INTER_AREA)
        if small.ndim == 3:
            small = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
        avg = np.mean(small)
        bits = (small > avg).flatten()
        hash_int = 0
        for i, bit in enumerate(bits):
            if bit:
                hash_int |= 1 << i
        return hash_int


def wait_for_change(
    screenshot_provider: Callable,
    previous_screenshot: Image.Image,
    timeout: float = 5.0,
    threshold: float = 0.05,
    interval: float = 0.2,
) -> bool:
    """
    等待画面发生显著变化（替代固定 sleep）

    :param screenshot_provider: 返回 PIL.Image 的可调用对象
    :param previous_screenshot: 变化前的参考截图
    :param timeout: 最大等待秒数
    :param threshold: 变化阈值
    :param interval: 轮询间隔秒数
    :return: True=检测到变化, False=超时
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        current = screenshot_provider()
        if current is None:
            time.sleep(interval)
            continue
        if ImageDiff.is_significant_change(previous_screenshot, current, threshold):
            return True
        time.sleep(interval)
    return False


def wait_for_stable(
    screenshot_provider: Callable,
    timeout: float = 5.0,
    stable_count: int = 3,
    threshold: float = 0.03,
    interval: float = 0.2,
) -> Optional[Image.Image]:
    """
    等待画面稳定（多次采样无明显变化后返回）

    :param screenshot_provider: 返回 PIL.Image 的可调用对象
    :param timeout: 最大等待秒数
    :param stable_count: 连续稳定帧数要求
    :param threshold: 变化阈值
    :param interval: 轮询间隔秒数
    :return: 稳定后的截图；超时返回 None
    """
    frames: list[Image.Image] = []
    deadline = time.time() + timeout

    while time.time() < deadline:
        current = screenshot_provider()
        if current is None:
            time.sleep(interval)
            continue

        frames.append(current)
        if len(frames) < 2:
            time.sleep(interval)
            continue

        # 只保留最近 stable_count + 1 帧
        if len(frames) > stable_count + 1:
            frames.pop(0)

        # 检查最近 stable_count 对差异是否都低于阈值
        recent = frames[-(stable_count + 1):]
        all_stable = True
        for i in range(len(recent) - 1):
            if ImageDiff.calculate_diff_ratio(recent[i], recent[i + 1]) >= threshold:
                all_stable = False
                break

        if all_stable:
            return current

        time.sleep(interval)

    return None
