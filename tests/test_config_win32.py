"""覆盖 F-04、F-05、R-05：配置及窗口标题规则测试。"""

import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from sf6_helper.config import AppConfig, user_data_root
from sf6_helper.win32 import title_matches, virtual_key


class ConfigAndWindowTests(unittest.TestCase):
    def test_title_matching_is_case_insensitive(self) -> None:
        config = AppConfig(window_titles="Street Fighter 6|StreetFighter6")
        self.assertTrue(title_matches("STREET FIGHTER 6", config.title_candidates))
        self.assertFalse(title_matches("记事本", config.title_candidates))

    def test_title_matching_ignores_trademark_and_spaces(self) -> None:
        config = AppConfig(window_titles="StreetFighter6")
        self.assertTrue(title_matches("Street Fighter™ 6", config.title_candidates))

    def test_invalid_minimum_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            AppConfig(min_bars=0).validate()

    def test_default_keys_resolve(self) -> None:
        self.assertEqual(0x09, virtual_key("tab"))
        self.assertEqual(0x0D, virtual_key("enter"))
        self.assertEqual(0x28, virtual_key("down"))

    def test_source_data_root_is_project_directory(self) -> None:
        self.assertEqual("sf6-battle-helper", user_data_root().name)

    def test_old_enter_config_migrates_to_tab(self) -> None:
        with TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text(json.dumps({"accept_key": "enter", "reject_confirm_key": "enter"}), encoding="utf-8")
            config = AppConfig.load(path)
            self.assertEqual("f", config.accept_key)
            self.assertEqual("s", config.reject_move_key)
            self.assertEqual("f", config.reject_confirm_key)

    def test_v2_tab_config_migrates_to_sf6_menu_keys(self) -> None:
        with TemporaryDirectory() as folder:
            path = Path(folder) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "config_version": 2,
                        "accept_key": "tab",
                        "reject_move_key": "down",
                        "reject_confirm_key": "tab",
                    }
                ),
                encoding="utf-8",
            )
            config = AppConfig.load(path)
            self.assertEqual(("f", "s", "f"), (config.accept_key, config.reject_move_key, config.reject_confirm_key))


if __name__ == "__main__":
    unittest.main()
