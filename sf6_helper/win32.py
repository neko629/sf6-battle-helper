"""覆盖 F-01、F-06、R-01、R-05、R-06：窗口捕获、前台校验与 SendInput。"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import PureWindowsPath
import time

import numpy as np
from PIL import ImageGrab


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_SCANCODE = 0x0008
VK_F8 = 0x77
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
MAPVK_VK_TO_VSC = 0
EXTENDED_KEYS = {0x25, 0x26, 0x27, 0x28}


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD), ("wParamH", wintypes.WORD)]


class INPUT_UNION(ctypes.Union):
    # SendInput 要求联合体保持 Windows INPUT 的完整原生大小。
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


VK_NAMES = {
    "tab": 0x09,
    "enter": 0x0D,
    "return": 0x0D,
    "escape": 0x1B,
    "esc": 0x1B,
    "space": 0x20,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
}


def foreground_window() -> tuple[int, str, tuple[int, int, int, int] | None]:
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return 0, "", None
    length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer, len(buffer))
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        return hwnd, buffer.value, None
    if rect.right <= rect.left or rect.bottom <= rect.top:
        return hwnd, buffer.value, None
    return hwnd, buffer.value, (rect.left, rect.top, rect.right, rect.bottom)


def title_matches(title: str, candidates: tuple[str, ...]) -> bool:
    # 忽略空格、商标符号和标点，例如 Street Fighter™ 6。
    normalized = "".join(character for character in title.casefold() if character.isalnum())
    return any(
        "".join(character for character in candidate if character.isalnum()) in normalized
        for candidate in candidates
    )


def foreground_process_name(hwnd: int) -> str:
    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    if not process_id.value:
        return ""
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id.value)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        if not kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return ""
        return PureWindowsPath(buffer.value).name
    finally:
        kernel32.CloseHandle(handle)


def game_window_matches(hwnd: int, title: str, candidates: tuple[str, ...]) -> bool:
    return title_matches(title, candidates) or foreground_process_name(hwnd).casefold() == "streetfighter6.exe"


def capture_foreground(candidates: tuple[str, ...]) -> tuple[np.ndarray | None, str]:
    hwnd, title, rect = foreground_window()
    if rect is None or not game_window_matches(hwnd, title, candidates):
        return None, title
    image = ImageGrab.grab(bbox=rect, all_screens=True)
    rgb = np.asarray(image.convert("RGB"))
    return rgb[:, :, ::-1].copy(), title


def virtual_key(name: str) -> int:
    normalized = name.strip().casefold()
    if normalized in VK_NAMES:
        return VK_NAMES[normalized]
    if len(normalized) == 1:
        code = user32.VkKeyScanW(ord(normalized))
        if code != -1:
            return code & 0xFF
    raise ValueError(f"不支持的按键：{name}")


def _send_vk(vk: int, key_up: bool) -> None:
    scan_code = user32.MapVirtualKeyW(vk, MAPVK_VK_TO_VSC)
    if not scan_code:
        raise ValueError(f"无法映射按键代码：{vk}")
    flags = KEYEVENTF_SCANCODE
    if vk in EXTENDED_KEYS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if key_up:
        flags |= KEYEVENTF_KEYUP
    event = INPUT(type=INPUT_KEYBOARD, union=INPUT_UNION(ki=KEYBDINPUT(0, scan_code, flags, 0, None)))
    sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError()


def press_key(name: str, hold_seconds: float = 0.12) -> None:
    vk = virtual_key(name)
    _send_vk(vk, False)
    time.sleep(hold_seconds)
    _send_vk(vk, True)


def f8_pressed_once(previous_down: bool) -> tuple[bool, bool]:
    down = bool(user32.GetAsyncKeyState(VK_F8) & 0x8000)
    return down and not previous_down, down
