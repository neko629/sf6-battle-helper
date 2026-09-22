"""匹配确认顺序门禁：必须先完成第一步，才允许进入网络判断。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FlowPhase(str, Enum):
    WAIT_PROMPT = "wait_prompt"
    WAIT_NETWORK = "wait_network"


@dataclass(slots=True)
class MatchFlowGate:
    confirm_frames: int = 2
    network_timeout_seconds: float = 8.0
    phase: FlowPhase = FlowPhase.WAIT_PROMPT
    prompt_hits: int = 0
    network_hits: int = 0
    network_deadline: float = 0.0

    def observe(self, kind: str, now: float) -> str | None:
        if self.phase is FlowPhase.WAIT_NETWORK and now > self.network_deadline:
            self.reset()
            return "network_timeout"

        if self.phase is FlowPhase.WAIT_PROMPT:
            self.network_hits = 0
            if kind == "prompt":
                self.prompt_hits += 1
                if self.prompt_hits >= self.confirm_frames:
                    return "reveal"
            else:
                self.prompt_hits = 0
            # 网络框在第一步之前出现时必须忽略。
            return None

        self.prompt_hits = 0
        if kind == "network":
            self.network_hits += 1
            if self.network_hits >= self.confirm_frames:
                return "decide"
        else:
            self.network_hits = 0
        return None

    def arm_network(self, now: float) -> None:
        self.phase = FlowPhase.WAIT_NETWORK
        self.prompt_hits = 0
        self.network_hits = 0
        self.network_deadline = now + self.network_timeout_seconds

    def reset(self) -> None:
        self.phase = FlowPhase.WAIT_PROMPT
        self.prompt_hits = 0
        self.network_hits = 0
        self.network_deadline = 0.0

