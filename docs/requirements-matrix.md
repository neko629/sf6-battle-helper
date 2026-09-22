# 需求—实现对齐矩阵

## 材料盘点

- 功能描述：已提供。
- UI/原型：已提供 4 张游戏截图。
- 流程规则：已提供“匹配后按 Tab，再读取网络信息”。
- 技术架构：用户确认 Python + OpenCV + Windows SendInput。
- 字段：由用户确认项直接形成配置字段。
- 已有代码：目标目录为空。

## 功能与规则

| 编号 | 内容 | 实现位置 | 状态 |
|---|---|---|---|
| F-01 | 识别首次匹配提示并按 Tab | `recognizer.py`, `worker.py` | 已完成 |
| F-02 | 区分 Wi-Fi/有线并识别信号格数 | `recognizer.py` | 已完成 |
| F-03 | 按条件接受或拒绝 | `decision.py`, `worker.py` | 已完成 |
| F-04 | 配置是否允许 Wi-Fi | `app.py`, `config.py` | 已完成 |
| F-05 | 配置最低信号格数和按键 | `app.py`, `config.py` | 已完成 |
| F-06 | 开始、停止、F8 紧急停止、日志 | `app.py`, `worker.py`, `win32.py` | 已完成 |
| R-01 | 详情页优先于首次提示识别 | `recognizer.py` | 已完成 |
| R-02 | 彩色竖条为有线，圆点/弧段为 Wi-Fi | `recognizer.py` | 已完成 |
| R-03 | 禁止 Wi-Fi 时一律拒绝 | `decision.py` | 已完成 |
| R-04 | 信号低于门槛时拒绝，否则接受 | `decision.py` | 已完成 |
| R-05 | 仅游戏窗口在前台时输入 | `win32.py`, `worker.py` | 已完成 |
| R-06 | 每次输入前再次检查前台窗口 | `worker.py` | 已完成 |
| R-07 | 冷却和状态去重防止重复输入 | `worker.py` | 已完成 |

## 页面交互

| 编号 | 内容 | 状态 |
|---|---|---|
| P-01 | 匹配规则区 | 已完成 |
| P-02 | 窗口和按键配置区 | 已完成 |
| P-03 | 状态与滚动日志区 | 已完成 |
| P-04 | 开始、停止、调试截图操作 | 已完成 |

## 字段

| 字段 | 类型 | 约束 |
|---|---|---|
| allow_wifi | bool | 必填 |
| min_bars | int | 1..5 |
| window_titles | string | `|` 分隔，至少一个 |
| reveal_key | string | 非空 |
| accept_key | string | 非空 |
| reject_move_key | string | 非空 |
| reject_confirm_key | string | 非空 |

