# lerobot_teleoperator_teleop

`lerobot_teleoperator_teleop` 是一个 LeRobot teleoperator 适配包。它本身不实现完整的主从遥操作系统，而是在已经存在的遥操作系统基础上，通过 ZMQ 接收主端控制指令，并把这些指令转换成 LeRobot 框架能够消费的 action。

换句话说，这个包的定位是：

```text
已有遥操作系统主端/主臂 ROS 节点
        |
        | ZMQ: control_pos
        v
lerobot_teleoperator_teleop
        |
        | LeRobot Teleoperator.get_action()
        v
LeRobot robot / dataset / policy pipeline
        |
        | 机器人侧控制接口，可继续通过 ZMQ 转发
        v
从端/从臂 ROS 节点
```

项目适合用于把已有的 C++/ROS 遥操作系统接入 LeRobot，例如使用 LeRobot 进行数据采集、动作封装、机器人接口统一管理或后续模仿学习数据处理。

## 功能概述

- 注册一个 LeRobot `Teleoperator` 子类，名称为 `teleop`。
- 通过 `TeleopConfig` 注册 LeRobot 配置类型 `lerobot_teleoperator_teleop`。
- 订阅已有遥操作系统通过 ZMQ 发布的控制量。
- 将收到的 `control_pos` 映射为 LeRobot action 字典。
- 默认支持 7 个机械臂关节和 1 个夹爪自由度。
- 不负责底层遥操作控制、ROS 节点启动、机器人驱动或从臂通信。

## 代码结构

```text
.
├── pyproject.toml
└── lerobot_teleoperator_teleop
    ├── __init__.py
    ├── config_teleop.py
    ├── teleop.py
    └── readme.txt
```

核心文件说明：

- `lerobot_teleoperator_teleop/teleop.py`
  - 定义 `Teleop` 类。
  - 继承 `lerobot.teleoperators.teleoperator.Teleoperator`。
  - 在 `connect()` 中创建 ZMQ subscriber。
  - 在 `get_action()` 中从 ZMQ 读取遥操作指令并转成 LeRobot action。

- `lerobot_teleoperator_teleop/config_teleop.py`
  - 定义 `TeleopConfig`。
  - 通过 `@TeleoperatorConfig.register_subclass("lerobot_teleoperator_teleop")` 注册配置类型。
  - 当前仅包含 `use_gripper: bool = True` 配置项。

- `pyproject.toml`
  - 定义 Python 包信息和依赖。
  - 包名为 `lerobot_teleoperator_teleop`。
  - 依赖包括 `numpy`、`teleop` 和 `lerobot>=0.4`。

## 数据流和通信约定

### ZMQ 订阅端

当前代码在 `Teleop.connect()` 中固定连接：

```python
ZMQStateSub("tcp://127.0.0.1:5557")
```

因此，已有遥操作系统需要在本机 `5557` 端口发布控制指令。如果主端遥操作程序不在同一台机器上运行，需要把代码里的地址改成对应的 IP，例如：

```python
ZMQStateSub("tcp://192.168.x.x:5557")
```

### 输入消息格式

`Teleop.get_action()` 会调用：

```python
last_robot_command = self._command_sub.get_obs()
```

并期望返回值是一个包含 `control_pos` 字段的字典：

```python
{
    "control_pos": [...]
}
```

`control_pos` 会被转换成 `np.float32` 数组，并按如下方式映射：

| `control_pos` 索引 | LeRobot action key |
| --- | --- |
| `0` | `joint_1.cmd_pos` |
| `1` | `joint_2.cmd_pos` |
| `2` | `joint_3.cmd_pos` |
| `3` | `joint_4.cmd_pos` |
| `4` | `joint_5.cmd_pos` |
| `5` | `joint_6.cmd_pos` |
| `6` | `joint_7.cmd_pos` |
| `7` | `gripper.cmd_pos`，仅当 `use_gripper=True` |

也就是说，默认情况下 `control_pos` 至少需要包含 8 个元素：

```python
control_pos = [
    joint_1,
    joint_2,
    joint_3,
    joint_4,
    joint_5,
    joint_6,
    joint_7,
    gripper,
]
```

如果 `use_gripper=False`，则只会读取前 7 个关节位置。

### 输出 action 格式

当收到有效控制指令时，`get_action()` 返回：

```python
{
    "joint_1.cmd_pos": float,
    "joint_2.cmd_pos": float,
    "joint_3.cmd_pos": float,
    "joint_4.cmd_pos": float,
    "joint_5.cmd_pos": float,
    "joint_6.cmd_pos": float,
    "joint_7.cmd_pos": float,
    "gripper.cmd_pos": float,
}
```

当 ZMQ 暂时没有收到数据时，`get_action()` 返回空字典：

```python
{}
```

## 与 LeRobot 的接口关系

`Teleop` 实现了 LeRobot teleoperator 所需的主要接口：

```python
class Teleop(Teleoperator):
    config_class = TeleopConfig
    name = "teleop"
```

### `action_features`

`action_features` 用来告诉 LeRobot 该 teleoperator 会输出哪些 action 字段：

```python
{
    "joint_1.cmd_pos": float,
    "joint_2.cmd_pos": float,
    ...
    "joint_7.cmd_pos": float,
    "gripper.cmd_pos": float,
}
```

如果 `use_gripper=False`，则不会包含 `gripper.cmd_pos`。

### `feedback_features`

当前返回空字典：

```python
{}
```

这表示该 teleoperator 目前只从已有遥操作系统接收控制指令，不向主端反馈机器人状态、力反馈或触觉反馈。

### `connect()`

`connect()` 会：

1. 将 `_connected` 标记为 `True`。
2. 创建 ZMQ 订阅对象。

当前实现不会检查外部遥操作系统是否真的已经启动，也不会做握手确认。

### `calibrate()` 和 `configure()`

当前为空实现：

```python
def calibrate(self) -> None:
    pass

def configure(self) -> None:
    pass
```

原因是该包假设标定、零点设置、遥操作主从映射等工作已经在原有遥操作系统中完成。LeRobot 侧只负责拿到已经处理好的控制目标。

## 环境依赖

建议 Python 版本：

```text
Python >= 3.10
```

Python 依赖：

```text
numpy
teleop
lerobot>=0.4
```

此外，代码中还有一个本地路径依赖：

```python
sys.path.append('/home/robot/01_remote_control_new/src')
from teleoperation_system.scripts.dynamixel_state_pub_zmq import ZMQStateSub
```

这说明运行环境需要能够访问已有遥操作系统中的 `teleoperation_system` 包，并且其中需要提供 `ZMQStateSub` 类。

如果你的遥操作系统路径不同，需要修改 `teleop.py` 中的路径：

```python
sys.path.append('/path/to/your/remote_control_system/src')
```

更推荐的长期做法是把已有遥操作系统安装成 Python 包，或者通过 `PYTHONPATH` 暴露，而不是在代码里写死绝对路径。

## 安装

在本项目根目录执行：

```bash
pip install -e .
```

如果 LeRobot 安装在独立 conda 环境中，需要先激活对应环境：

```bash
conda activate <your_lerobot_env>
pip install -e .
```

安装后，LeRobot 应该能够导入：

```python
from lerobot_teleoperator_teleop.teleop import Teleop
from lerobot_teleoperator_teleop.config_teleop import TeleopConfig
```

## 使用方式

### 1. 启动已有遥操作系统

先启动原有主端遥操作系统，确保它会通过 ZMQ 发布控制指令到：

```text
tcp://127.0.0.1:5557
```

并且发布的数据中包含 `control_pos`。

典型链路可以是：

```text
主臂 ROS/C++ 节点 -> ZMQ publisher -> tcp://127.0.0.1:5557
```

### 2. 在 LeRobot 中选择该 teleoperator

该包注册的配置类型是：

```text
lerobot_teleoperator_teleop
```

实际使用时，需要在 LeRobot 的 teleoperator 配置中选择这个类型。具体命令取决于你当前使用的 LeRobot 入口脚本和配置方式。

如果是 Python 代码中直接使用，可以参考：

```python
from lerobot_teleoperator_teleop.config_teleop import TeleopConfig
from lerobot_teleoperator_teleop.teleop import Teleop

config = TeleopConfig(use_gripper=True)
teleop = Teleop(config)

teleop.connect()
action = teleop.get_action()
teleop.disconnect()
```

### 3. 检查 action 是否正常输出

可以用一个简单脚本确认 ZMQ 指令是否已经进入 LeRobot teleoperator：

```python
from lerobot_teleoperator_teleop.config_teleop import TeleopConfig
from lerobot_teleoperator_teleop.teleop import Teleop

teleop = Teleop(TeleopConfig(use_gripper=True))
teleop.connect()

while True:
    action = teleop.get_action()
    if action:
        print(action)
```

如果一直输出空字典，通常说明：

- ZMQ publisher 没有启动。
- 地址或端口不一致。
- `ZMQStateSub.get_obs()` 没有收到数据。
- 收到的数据里没有 `control_pos` 字段。

## 配置项

当前只有一个配置项：

| 配置项 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `use_gripper` | `bool` | `True` | 是否从 `control_pos[7]` 读取夹爪目标位置并输出 `gripper.cmd_pos` |

示例：

```python
TeleopConfig(use_gripper=True)
```

如果机器人没有夹爪，或者 LeRobot robot action space 中没有 `gripper.cmd_pos`，可以使用：

```python
TeleopConfig(use_gripper=False)
```

## 当前实现的限制

- ZMQ 地址被写死为 `tcp://127.0.0.1:5557`。
- 已有遥操作系统路径被写死为 `/home/robot/01_remote_control_new/src`。
- 没有对 ZMQ 连接状态做显式检查。
- 没有对 `control_pos` 长度做保护性检查。
- 没有实现机器人状态反馈、力反馈或触觉反馈。
- `calibrate()` 和 `configure()` 是空实现，默认这些流程由已有遥操作系统负责。
- `disconnect()` 只修改连接状态，没有显式关闭 ZMQ subscriber。

这些限制不影响它作为最小 LeRobot 适配层使用，但如果要长期维护，建议逐步把 ZMQ 地址、本地遥操作系统路径、关节数量和夹爪索引都改成配置项。

## 常见问题

### 为什么没有实现完整遥操作逻辑？

因为该项目的目标不是重写遥操作系统，而是复用已经存在的遥操作系统。原系统负责主端采集、映射、滤波、约束和底层通信；本项目只负责把原系统输出的目标位置接入 LeRobot。

### 为什么 `get_action()` 有时返回空字典？

当 ZMQ 订阅端没有收到新数据时，`ZMQStateSub.get_obs()` 返回 `None`，此时 `get_action()` 会返回 `{}`。

### LeRobot 中的关节名必须是 `joint_1.cmd_pos` 这种格式吗？

当前代码写死了这个 action key 格式。机器人侧的 action feature 需要与这些 key 对齐。如果你的 LeRobot robot 使用不同的关节命名，需要同步修改 `action_features` 和 `get_action()` 中的 key。

### 夹爪可以不用吗？

可以。创建配置时设置：

```python
TeleopConfig(use_gripper=False)
```

这样 action 中只会包含 7 个机械臂关节。

## 建议的后续改进

- 将 ZMQ 地址改成 `TeleopConfig` 配置项。
- 将已有遥操作系统 Python 路径改成环境变量或安装依赖。
- 对 `control_pos` 做字段存在性和长度检查。
- 在 `disconnect()` 中关闭 ZMQ socket。
- 根据实际机器人模型，把关节名称、关节数量和夹爪字段做成可配置。
- 如果需要双向遥操作，扩展 `send_feedback()`，把 LeRobot robot feedback 通过 ZMQ 发回主端。
