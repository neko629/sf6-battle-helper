"""覆盖 F-03、R-03、R-04：连接条件判定。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .config import AppConfig


class ConnectionType(str, Enum):
    WIRED = "wired"
    WIFI = "wifi"


@dataclass(frozen=True, slots=True)
class NetworkStatus:
    connection: ConnectionType
    bars: int
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class Decision:
    accept: bool
    reason: str


def decide(status: NetworkStatus, config: AppConfig) -> Decision:
    if status.connection is ConnectionType.WIFI and not config.allow_wifi:
        return Decision(False, "Wi-Fi 对手未被允许")
    if status.bars < config.min_bars:
        return Decision(False, f"信号 {status.bars} 格，低于要求的 {config.min_bars} 格")
    label = "Wi-Fi" if status.connection is ConnectionType.WIFI else "有线"
    return Decision(True, f"{label} {status.bars} 格，满足条件")

