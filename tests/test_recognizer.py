"""覆盖 F-01、F-02、R-01、R-02：用户截图离线回归测试。"""

from pathlib import Path
import unittest
import cv2
import numpy as np

from sf6_helper.decision import ConnectionType
from sf6_helper.recognizer import ScreenRecognizer, read_image


ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "img-examples"


class RecognizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.recognizer = ScreenRecognizer(EXAMPLES)

    def _recognize_named(self, fragment: str):
        path = next(path for path in EXAMPLES.glob("*.png") if fragment in path.name)
        return self.recognizer.recognize(read_image(path))

    def test_prompt(self) -> None:
        result = self._recognize_named("匹配到对手")
        self.assertEqual("prompt", result.kind)

    def test_wired_two_bars(self) -> None:
        result = self._recognize_named("有线2格")
        self.assertEqual("network", result.kind)
        self.assertEqual(ConnectionType.WIRED, result.network.connection)
        self.assertEqual(2, result.network.bars)

    def test_wired_four_bars(self) -> None:
        result = self._recognize_named("有线4格")
        self.assertEqual("network", result.kind)
        self.assertEqual(ConnectionType.WIRED, result.network.connection)
        self.assertEqual(4, result.network.bars)

    def test_wifi_one_bar(self) -> None:
        result = self._recognize_named("wifi1格")
        self.assertEqual("network", result.kind)
        self.assertEqual(ConnectionType.WIFI, result.network.connection)
        self.assertEqual(1, result.network.bars)

    def test_fullscreen_prompt(self) -> None:
        result = self._recognize_named("对战提示框全局位置")
        self.assertEqual("prompt", result.kind)
        self.assertGreater(result.confidence, 0.90)

    def test_detail_is_not_prompt(self) -> None:
        path = next(path for path in EXAMPLES.glob("*.png") if "信号确认框全局位置" in path.name)
        self.assertLess(self.recognizer.detect_prompt(read_image(path)), 0.58)

    def test_fullscreen_wired_one_bar(self) -> None:
        result = self._recognize_named("信号确认框全局位置")
        self.assertEqual("network", result.kind)
        self.assertEqual(ConnectionType.WIRED, result.network.connection)
        self.assertEqual(1, result.network.bars)

    def test_colored_dot_without_purple_dialog_is_not_network(self) -> None:
        image = np.full((900, 1600, 3), (38, 25, 18), dtype=np.uint8)
        cv2.circle(image, (800, 450), 6, (20, 30, 230), thickness=-1)
        self.assertIsNone(self.recognizer.detect_network(image))

    def test_purple_scene_without_confirm_buttons_is_not_network(self) -> None:
        image = np.full((900, 1600, 3), (90, 15, 95), dtype=np.uint8)
        cv2.rectangle(image, (795, 430), (800, 450), (20, 120, 230), thickness=-1)
        self.assertIsNone(self.recognizer.detect_network(image))

    def test_fullscreen_prompt_is_not_network(self) -> None:
        path = next(path for path in EXAMPLES.glob("*.png") if "对战提示框全局位置" in path.name)
        self.assertIsNone(self.recognizer.detect_network(read_image(path)))


if __name__ == "__main__":
    unittest.main()
