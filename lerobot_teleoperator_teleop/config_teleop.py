from dataclasses import dataclass

from lerobot.teleoperators.config import TeleoperatorConfig


@TeleoperatorConfig.register_subclass("lerobot_teleoperator_teleop")
@dataclass
class TeleopConfig(TeleoperatorConfig):
    use_gripper: bool = True
