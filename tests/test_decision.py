"""覆盖 R-03、R-04：匹配条件单元测试。"""

import unittest

from sf6_helper.config import AppConfig
from sf6_helper.decision import ConnectionType, NetworkStatus, decide


class DecisionTests(unittest.TestCase):
    def test_rejects_wifi_when_disabled(self) -> None:
        result = decide(NetworkStatus(ConnectionType.WIFI, 5), AppConfig(allow_wifi=False, min_bars=1))
        self.assertFalse(result.accept)

    def test_rejects_below_minimum(self) -> None:
        result = decide(NetworkStatus(ConnectionType.WIRED, 2), AppConfig(min_bars=3))
        self.assertFalse(result.accept)

    def test_accepts_at_minimum(self) -> None:
        result = decide(NetworkStatus(ConnectionType.WIFI, 3), AppConfig(allow_wifi=True, min_bars=3))
        self.assertTrue(result.accept)


if __name__ == "__main__":
    unittest.main()

