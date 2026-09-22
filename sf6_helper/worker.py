"""覆盖 F-01~F-03、F-06、R-01~R-07：监控状态机。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import threading
import time
from typing import Callable

import cv2

from .config import AppConfig
from .decision import decide
from .flow import FlowPhase, MatchFlowGate
from .recognizer import ScreenRecognizer
from .win32 import capture_foreground, f8_pressed_once, foreground_window, game_window_matches, press_key


LogCallback = Callable[[str], None]
StateCallback = Callable[[str], None]


@dataclass(slots=True)
class WorkerCallbacks:
    log: LogCallback
    state: StateCallback


class MonitorWorker:
    def __init__(self, config: AppConfig, recognizer: ScreenRecognizer, callbacks: WorkerCallbacks) -> None:
        self.config = config
        self.recognizer = recognizer
        self.callbacks = callbacks
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self.config.validate()
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="sf6-monitor", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _game_still_foreground(self) -> bool:
        hwnd, title, _ = foreground_window()
        return game_window_matches(hwnd, title, self.config.title_candidates)

    def _safe_press(self, key: str) -> bool:
        if self._stop.is_set() or not self._game_still_foreground():
            self.callbacks.log("输入已取消：游戏不在前台")
            return False
        press_key(key)
        return True

    def _run(self) -> None:
        self.callbacks.state("监控中（F8 紧急停止）")
        self.callbacks.log("开始监控，仅在游戏处于前台时工作")
        last_action = 0.0
        last_kind = "none"
        flow = MatchFlowGate()
        f8_was_down = False
        try:
            while not self._stop.is_set():
                triggered, f8_was_down = f8_pressed_once(f8_was_down)
                if triggered:
                    self.callbacks.log("F8 紧急停止已触发")
                    self._stop.set()
                    break

                frame, title = capture_foreground(self.config.title_candidates)
                if frame is None:
                    if last_kind != "waiting-window":
                        self.callbacks.state("等待游戏窗口置于前台")
                        self.callbacks.log(f"当前前台窗口：{title or '无标题'}")
                    last_kind = "waiting-window"
                    self._stop.wait(0.25)
                    continue

                recognition = self.recognizer.recognize(frame)
                now = time.monotonic()
                flow_event = flow.observe(recognition.kind, now)
                if flow_event == "network_timeout":
                    self.callbacks.log("等待网络详情超时，已回到第一步")
                    self.callbacks.state("等待匹配")
                cooled_down = (now - last_action) * 1000 >= self.config.action_cooldown_ms
                if flow_event == "reveal" and cooled_down:
                    self.callbacks.log(f"检测到首次确认（置信度 {recognition.confidence:.2f}），按 {self.config.reveal_key}")
                    if self._safe_press(self.config.reveal_key):
                        last_action = time.monotonic()
                        last_kind = "prompt-action"
                        flow.arm_network(last_action)
                        self.callbacks.state("等待网络详情")
                elif flow_event == "decide" and recognition.network is not None and cooled_down:
                    status = recognition.network
                    result = decide(status, self.config)
                    connection = "Wi-Fi" if status.connection.value == "wifi" else "有线"
                    self.callbacks.log(f"识别：{connection} {status.bars} 格（置信度 {status.confidence:.2f}）— {result.reason}")
                    if result.accept:
                        self.callbacks.log(f"发送接受操作：{self.config.accept_key}")
                        ok = self._safe_press(self.config.accept_key)
                        action = "已发送接受操作"
                    else:
                        self.callbacks.log(
                            f"发送拒绝操作：{self.config.reject_move_key} → {self.config.reject_confirm_key}"
                        )
                        ok = self._safe_press(self.config.reject_move_key)
                        if ok:
                            time.sleep(0.09)
                            ok = self._safe_press(self.config.reject_confirm_key)
                        action = "已发送拒绝操作"
                    if ok:
                        self.callbacks.log(action)
                        last_action = time.monotonic()
                        last_kind = "network-action"
                        flow.reset()
                        self.callbacks.state(action)
                elif recognition.kind == "none" and flow.phase is FlowPhase.WAIT_PROMPT:
                    if last_kind not in ("none", "waiting"):
                        self.callbacks.state("等待匹配")
                    last_kind = "none"

                self._stop.wait(self.config.scan_interval_ms / 1000)
        except Exception as exc:  # 保持 GUI 存活并报告设备/输入错误。
            self.callbacks.log(f"监控错误：{exc}")
        finally:
            self.callbacks.state("已停止")


def save_debug_capture(config: AppConfig, output_dir: Path) -> Path:
    frame, title = capture_foreground(config.title_candidates)
    if frame is None:
        raise RuntimeError(f"游戏窗口未在前台；当前窗口：{title or '无标题'}")
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = time.strftime("capture-%Y%m%d-%H%M%S.png")
    path = output_dir / filename
    ok, encoded = cv2.imencode(".png", frame)
    if not ok:
        raise RuntimeError("截图编码失败")
    encoded.tofile(path)
    return path
