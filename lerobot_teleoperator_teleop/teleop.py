from typing import Any
import numpy as np
import sys
sys.path.append('/home/robot/01_remote_control_new/src')

from teleoperation_system.scripts.dynamixel_state_pub_zmq import ZMQStateSub # type: ignore

from lerobot.teleoperators.teleoperator import Teleoperator
from lerobot_teleoperator_teleop.config_teleop import TeleopConfig

class Teleop(Teleoperator):
    config_class = TeleopConfig
    name = "teleop"
 
    def __init__(self, config: TeleopConfig):
        super().__init__(config)
        self.config = config
        self._connected = False
        self._calibrated = True
        self._command_sub = None

        self._last_joint_command = np.zeros(7, dtype=np.float32)
        self._last_gripper_command = np.zeros(1, dtype=np.float32)

    @property
    def action_features(self) -> dict[str, type]:
        motors = {f"joint_{i}.cmd_pos": float for i in range(1, 8)}
        if self.config.use_gripper:
            motors["gripper.cmd_pos"] = float
        return motors

    @property
    def feedback_features(self) -> dict[str, type]:
        return {}

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, calibrate: bool = True) -> None:
        self._connected = True

        self._command_sub = ZMQStateSub("tcp://127.0.0.1:5557")

    @property
    def is_calibrated(self) -> bool:
        return self._calibrated

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        pass

    def get_action(self) -> dict[str, Any]:
        last_robot_command = self._command_sub.get_obs()

        action = {}
        if last_robot_command is None:
            return action

        control_pos = np.asarray(last_robot_command["control_pos"], dtype=np.float32)

        for i in range(1, 8):
            action[f"joint_{i}.cmd_pos"] = float(control_pos[i - 1])
        if self.config.use_gripper:
            action["gripper.cmd_pos"] = float(control_pos[7])
        
        return action

    def send_feedback(self, feedback: dict[str, float]) -> None:
        pass

    def disconnect(self) -> None:
        self._connected = False
