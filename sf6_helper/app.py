"""覆盖 F-04~F-06、P-01~P-04：Tkinter 配置与运行界面。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import queue
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from .config import AppConfig, user_data_root
from . import __version__
from .recognizer import ScreenRecognizer
from .worker import MonitorWorker, WorkerCallbacks, save_debug_capture


ASSET_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
DATA_ROOT = user_data_root()


class HelperApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(f"SF6 对战确认助手 v{__version__}")
        self.root.resizable(False, False)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.config = AppConfig.load()
        self.recognizer = ScreenRecognizer(ASSET_ROOT / "img-examples")
        self.worker: MonitorWorker | None = None

        self.allow_wifi = tk.BooleanVar(value=self.config.allow_wifi)
        self.min_bars = tk.IntVar(value=self.config.min_bars)
        self.window_titles = tk.StringVar(value=self.config.window_titles)
        self.reveal_key = tk.StringVar(value=self.config.reveal_key)
        self.accept_key = tk.StringVar(value=self.config.accept_key)
        self.reject_move_key = tk.StringVar(value=self.config.reject_move_key)
        self.reject_confirm_key = tk.StringVar(value=self.config.reject_confirm_key)
        self.status = tk.StringVar(value="已停止")
        self._build()
        self.root.after(100, self._drain_events)
        self.root.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.grid(sticky="nsew")

        rules = ttk.LabelFrame(outer, text="匹配规则", padding=10)
        rules.grid(row=0, column=0, sticky="ew")
        ttk.Checkbutton(rules, text="允许 Wi-Fi 对手", variable=self.allow_wifi).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(rules, text="最低信号格数：").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Spinbox(rules, from_=1, to=5, width=6, textvariable=self.min_bars, state="readonly").grid(row=1, column=1, sticky="w", pady=(8, 0))

        keys = ttk.LabelFrame(outer, text="窗口与按键", padding=10)
        keys.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        fields = (
            ("窗口标题（| 分隔）：", self.window_titles, 28),
            ("打开网络详情：", self.reveal_key, 12),
            ("接受：", self.accept_key, 12),
            ("拒绝时移动：", self.reject_move_key, 12),
            ("拒绝时确认：", self.reject_confirm_key, 12),
        )
        for row, (label, variable, width) in enumerate(fields):
            ttk.Label(keys, text=label).grid(row=row, column=0, sticky="w", pady=2)
            ttk.Entry(keys, textvariable=variable, width=width).grid(row=row, column=1, sticky="ew", pady=2)

        ttk.Label(outer, textvariable=self.status, foreground="#6a35b8").grid(row=2, column=0, sticky="w", pady=(10, 4))
        self.log = tk.Text(outer, width=62, height=9, state="disabled", wrap="word")
        self.log.grid(row=3, column=0)

        buttons = ttk.Frame(outer)
        buttons.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        self.start_button = ttk.Button(buttons, text="开始监控", command=self._start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(buttons, text="停止 / F8", command=self._stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        ttk.Button(buttons, text="保存调试截图", command=self._capture).pack(side="left")

    def _read_config(self) -> AppConfig:
        config = AppConfig(
            allow_wifi=self.allow_wifi.get(),
            min_bars=int(self.min_bars.get()),
            window_titles=self.window_titles.get(),
            reveal_key=self.reveal_key.get(),
            accept_key=self.accept_key.get(),
            reject_move_key=self.reject_move_key.get(),
            reject_confirm_key=self.reject_confirm_key.get(),
        )
        config.validate()
        return config

    def _start(self) -> None:
        try:
            self.config = self._read_config()
            self.config.save()
        except (ValueError, OSError) as exc:
            messagebox.showerror("配置错误", str(exc), parent=self.root)
            return
        callbacks = WorkerCallbacks(
            log=lambda message: self.events.put(("log", message)),
            state=lambda message: self.events.put(("state", message)),
        )
        self.worker = MonitorWorker(self.config, self.recognizer, callbacks)
        self.worker.start()
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")

    def _stop(self) -> None:
        if self.worker:
            self.worker.stop()
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")

    def _capture(self) -> None:
        try:
            self.config = self._read_config()
            path = save_debug_capture(self.config, DATA_ROOT / "debug-captures")
            self._append_log(f"调试截图已保存：{path}")
        except Exception as exc:
            messagebox.showerror("截图失败", str(exc), parent=self.root)

    def _append_log(self, message: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", f"[{datetime.now():%H:%M:%S}] {message}\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "log":
                    self._append_log(value)
                else:
                    self.status.set(value)
                    if value == "已停止":
                        self.start_button.configure(state="normal")
                        self.stop_button.configure(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)

    def _close(self) -> None:
        if self.worker:
            self.worker.stop()
        self.root.destroy()


def run() -> None:
    root = tk.Tk()
    HelperApp(root)
    root.mainloop()
