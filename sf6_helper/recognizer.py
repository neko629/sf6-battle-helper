"""覆盖 F-01、F-02、R-01、R-02：两阶段画面识别与信号计数。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .decision import ConnectionType, NetworkStatus


@dataclass(frozen=True, slots=True)
class Recognition:
    kind: str
    confidence: float
    network: NetworkStatus | None = None


def read_image(path: Path) -> np.ndarray:
    raw = np.fromfile(path, dtype=np.uint8)
    image = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"无法读取图片：{path}")
    return image


class ScreenRecognizer:
    def __init__(self, examples_dir: Path) -> None:
        prompt_files = list(examples_dir.glob("*匹配到对手*.png"))
        if not prompt_files:
            raise FileNotFoundError("img-examples 中缺少“匹配到对手”截图")
        prompt = read_image(prompt_files[0])
        height, width = prompt.shape[:2]
        # 用户样本中 Tab + 确认位于弹窗中央偏下；保留周围文字边缘以降低误报。
        self.prompt_template = prompt[
            int(height * 0.50) : int(height * 0.75),
            int(width * 0.525) : int(width * 0.625),
        ]
        if self.prompt_template.size == 0:
            raise ValueError("首次确认模板裁剪失败")

    @staticmethod
    def _active_signal_mask(image: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        blue, green, red = cv2.split(image)
        # 网络图标的有效格为红/橙/绿，排除紫色界面装饰。
        colorful = (hsv[:, :, 1] > 115) & (hsv[:, :, 2] > 85)
        non_magenta = blue.astype(np.float32) < np.maximum(red, green).astype(np.float32) * 0.72
        return (colorful & non_magenta).astype(np.uint8) * 255

    @staticmethod
    def _has_network_dialog(image: np.ndarray) -> bool:
        """验证紫色详情弹窗以及下方两条居中按钮边框同时存在。"""
        height, width = image.shape[:2]
        region = image[
            int(height * 0.22) : int(height * 0.72),
            int(width * 0.20) : int(width * 0.80),
        ]
        if region.size == 0:
            return False
        blue, green, red = cv2.split(region)
        green_f = green.astype(np.float32)
        purple = (
            (blue.astype(np.float32) > green_f * 1.25)
            & (red.astype(np.float32) > green_f * 1.25)
            & ((blue.astype(np.int16) + red.astype(np.int16)) > 90)
        )
        if float(np.mean(purple)) < 0.35:
            return False

        # “参战/取消”都有横跨画面中央的亮紫色水平边框。结果页虽为紫红色，
        # 但没有这组按钮，因此不能只依赖背景颜色。
        button_region = image[
            int(height * 0.48) : int(height * 0.72),
            int(width * 0.20) : int(width * 0.80),
        ]
        blue_b, green_b, red_b = cv2.split(button_region)
        magenta = (
            (red_b > 110)
            & (blue_b > 75)
            & (red_b.astype(np.float32) > green_b.astype(np.float32) * 1.35)
            & (blue_b.astype(np.float32) > green_b.astype(np.float32) * 1.15)
        )
        long_border_rows = np.sum(np.sum(magenta, axis=1) > width * 0.18)
        return int(long_border_rows) >= 2

    @staticmethod
    def detect_network(image: np.ndarray) -> NetworkStatus | None:
        if not ScreenRecognizer._has_network_dialog(image):
            return None
        height, width = image.shape[:2]
        y0, y1 = int(height * 0.40), int(height * 0.63)
        x0, x1 = int(width * 0.42), int(width * 0.60)
        roi = image[y0:y1, x0:x1]
        if roi.size == 0:
            return None
        mask = ScreenRecognizer._active_signal_mask(roi)
        count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
        components: list[tuple[int, int, int, int, int]] = []
        for x, y, w, h, area in stats[1:count]:
            if area < 10 or w > 55 or h > 55:
                continue
            center_x = x + w // 2
            center_y = y + h // 2
            patch = roi[
                max(0, center_y - 28) : min(roi.shape[0], center_y + 28),
                max(0, center_x - 28) : min(roi.shape[1], center_x + 28),
            ]
            if patch.size == 0:
                continue
            dark_fraction = float(np.mean(cv2.cvtColor(patch, cv2.COLOR_BGR2GRAY) < 55))
            # 图标有独立的近黑色方形底板；借此排除红色“排位赛”文字。
            if dark_fraction < 0.78:
                continue
            components.append((int(x), int(y), int(w), int(h), int(area)))
        if not components:
            return None

        # 取最接近 ROI 中心的一组。按钮、倒计时等彩色元素会因纵向位置或紫色被过滤。
        center_x = roi.shape[1] / 2
        center_y = roi.shape[0] / 2
        seed = min(
            components,
            key=lambda item: abs((item[0] + item[2] / 2) - center_x)
            + 0.6 * abs((item[1] + item[3] / 2) - center_y),
        )
        seed_cx = seed[0] + seed[2] / 2
        seed_cy = seed[1] + seed[3] / 2
        group = [
            item
            for item in components
            if abs((item[0] + item[2] / 2) - seed_cx) <= 45
            and abs((item[1] + item[3] / 2) - seed_cy) <= 45
        ]

        vertical = [item for item in group if item[3] >= 8 and item[3] >= item[2] * 1.35]
        if vertical:
            # 竖直彩色短条是有线图标；按彼此分离的竖条计数。
            bars = min(5, len(vertical))
            confidence = min(1.0, 0.62 + 0.09 * bars)
            return NetworkStatus(ConnectionType.WIRED, bars, confidence)

        # Wi-Fi 的圆点和弧段均为横向/近方形独立部件。
        wifi_parts = [item for item in group if item[4] >= 12]
        if wifi_parts:
            bars = max(1, min(5, len(wifi_parts)))
            confidence = min(1.0, 0.68 + 0.07 * bars)
            return NetworkStatus(ConnectionType.WIFI, bars, confidence)
        return None

    def detect_prompt(self, image: np.ndarray) -> float:
        height, width = image.shape[:2]
        # 实机全屏截图中提示框固定在屏幕下方。只搜索该区域，避免训练 HUD
        # 或背景文字偶然匹配小型 Tab 图标。旧的裁剪样本为超宽条形，保留更宽纵向范围。
        search_y0 = int(height * (0.30 if width / max(1, height) > 3.0 else 0.70))
        search_x0, search_x1 = int(width * 0.24), int(width * 0.76)
        search = image[search_y0 : int(height * 0.98), search_x0:search_x1]
        if search.size == 0:
            return -1.0
        source = cv2.Canny(cv2.cvtColor(search, cv2.COLOR_BGR2GRAY), 70, 160)
        best = -1.0
        for scale in (0.70, 0.80, 0.90, 1.00, 1.10, 1.20, 1.35, 1.50):
            template = cv2.resize(self.prompt_template, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            if template.shape[0] >= source.shape[0] or template.shape[1] >= source.shape[1]:
                continue
            edges = cv2.Canny(cv2.cvtColor(template, cv2.COLOR_BGR2GRAY), 70, 160)
            if np.count_nonzero(edges) < 15:
                continue
            score = float(cv2.minMaxLoc(cv2.matchTemplate(source, edges, cv2.TM_CCOEFF_NORMED))[1])
            best = max(best, score)
        return best

    def recognize(self, image: np.ndarray) -> Recognition:
        network = self.detect_network(image)
        if network is not None:
            return Recognition("network", network.confidence, network)
        prompt_score = self.detect_prompt(image)
        if prompt_score >= 0.58:
            return Recognition("prompt", prompt_score)
        return Recognition("none", max(0.0, prompt_score))
