"""严格验证“第一步 → 第二步”的状态顺序。"""

import unittest

from sf6_helper.flow import FlowPhase, MatchFlowGate


class MatchFlowGateTests(unittest.TestCase):
    def test_network_is_ignored_before_prompt(self) -> None:
        flow = MatchFlowGate()
        self.assertIsNone(flow.observe("network", 1.0))
        self.assertIsNone(flow.observe("network", 1.1))
        self.assertEqual(FlowPhase.WAIT_PROMPT, flow.phase)

    def test_two_prompt_frames_arm_first_action(self) -> None:
        flow = MatchFlowGate()
        self.assertIsNone(flow.observe("prompt", 1.0))
        self.assertEqual("reveal", flow.observe("prompt", 1.1))
        flow.arm_network(1.1)
        self.assertEqual(FlowPhase.WAIT_NETWORK, flow.phase)

    def test_network_decision_only_after_arm(self) -> None:
        flow = MatchFlowGate()
        flow.arm_network(2.0)
        self.assertIsNone(flow.observe("network", 2.1))
        self.assertEqual("decide", flow.observe("network", 2.2))

    def test_network_wait_times_out(self) -> None:
        flow = MatchFlowGate(network_timeout_seconds=8.0)
        flow.arm_network(3.0)
        self.assertEqual("network_timeout", flow.observe("none", 11.1))
        self.assertEqual(FlowPhase.WAIT_PROMPT, flow.phase)


if __name__ == "__main__":
    unittest.main()

