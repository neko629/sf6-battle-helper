"""覆盖 F-04、F-05、R-03、R-04：配置模型与持久化。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys


def user_data_root() -> Path:
    """源码运行时用项目目录；打包后用 EXE 所在目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


CONFIG_PATH = user_data_root() / "config.json"


@dataclass(slots=True)
class AppConfig:
    config_version: int = 3
    allow_wifi: bool = False
    min_bars: int = 3
    window_titles: str = "Street Fighter 6|StreetFighter6"
    reveal_key: str = "tab"
    accept_key: str = "f"
    reject_move_key: str = "s"
    reject_confirm_key: str = "f"
    scan_interval_ms: int = 120
    action_cooldown_ms: int = 1300

    def validate(self) -> None:
        if not 1 <= self.min_bars <= 5:
            raise ValueError("最低信号格数必须在 1 到 5 之间")
        if not 60 <= self.scan_interval_ms <= 2000:
            raise ValueError("扫描间隔必须在 60 到 2000 毫秒之间")
        if not 300 <= self.action_cooldown_ms <= 10000:
            raise ValueError("动作冷却必须在 300 到 10000 毫秒之间")
        if not any(part.strip() for part in self.window_titles.split("|")):
            raise ValueError("至少需要一个游戏窗口标题")
        for value in (
            self.reveal_key,
            self.accept_key,
            self.reject_move_key,
            self.reject_confirm_key,
        ):
            if not value.strip():
                raise ValueError("按键设置不能为空")

    @property
    def title_candidates(self) -> tuple[str, ...]:
        return tuple(part.strip().casefold() for part in self.window_titles.split("|") if part.strip())

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "AppConfig":
        if not path.exists():
            return cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # v1 使用 Enter 确认详情页；实机验证该弹窗仍使用 Tab。
            if int(data.get("config_version", 1)) < 2:
                if str(data.get("accept_key", "enter")).casefold() == "enter":
                    data["accept_key"] = "tab"
                if str(data.get("reject_confirm_key", "enter")).casefold() == "enter":
                    data["reject_confirm_key"] = "tab"
                data["config_version"] = 2
            # SF6 的 Tab 仅打开匹配详情；PC 菜单固定用 WASD 导航、F 确认。
            if int(data.get("config_version", 2)) < 3:
                if str(data.get("accept_key", "tab")).casefold() in {"enter", "tab"}:
                    data["accept_key"] = "f"
                if str(data.get("reject_move_key", "down")).casefold() == "down":
                    data["reject_move_key"] = "s"
                if str(data.get("reject_confirm_key", "tab")).casefold() in {"enter", "tab"}:
                    data["reject_confirm_key"] = "f"
                data["config_version"] = 3
            allowed = cls.__dataclass_fields__.keys()
            config = cls(**{key: value for key, value in data.items() if key in allowed})
            config.validate()
            return config
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return cls()

    def save(self, path: Path = CONFIG_PATH) -> None:
        self.validate()
        path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
