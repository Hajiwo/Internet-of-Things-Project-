# Smart Garage Sensors, Internal State, and Actuator Behavior / 智能车库传感器、内部状态与执行器行为说明

**Document purpose / 文档目的**

This document describes the currently supported sensors, the internal state maintained by the backend, and how the AI planner converts that information into actuator behavior.

本文档说明当前系统支持的传感器、Backend 内部维护的状态，以及 AI Planner 如何根据这些信息控制执行器。

**Last updated / 最后更新：** 2026-07-15

---

## 1. System Overview / 系统概览

The Smart Garage follows this event-driven data flow:

智能车库采用事件驱动的数据流程：

```text
Sensors and software events
传感器和软件事件
          │
          ▼
Raspberry Pi publishes MQTT; Camera API creates an internal event
树莓派发布 MQTT；Camera API 创建内部事件
          │
          ▼
Backend validates the message and updates Context
Backend 验证消息并更新 Context
          │
          ▼
AI Planner generates a PDDL problem and action plan
AI Planner 生成 PDDL 问题与动作计划
          │
          ▼
Executor publishes MQTT actuator commands
Executor 发布 MQTT 执行器命令
          │
          ▼
Relay, LED, and gate servo perform physical actions
Relay、LED 和门闸舵机执行物理动作
```

Every sensor or event topic maintains its own increasing `sequence_number`. The backend ignores duplicate or older messages.

每个传感器或事件 Topic 都维护独立递增的 `sequence_number`。Backend 会忽略重复消息或序号更小的旧消息。

---

## 2. Current Sensors and Input Events / 当前传感器与输入事件

### 2.1 Temperature and humidity sensor / 温湿度传感器

| Item / 项目 | Description / 说明 |
|---|---|
| Hardware / 硬件 | DHT11 |
| Interface / 接口 | GrovePi+ D2 |
| MQTT topic | `garage/sensor/temperature` |
| Backend field / Backend 字段 | `temperature` |
| Current use / 当前用途 | Fan planning / 风扇规划 |
| Humidity / 湿度 | Displayed locally on the LCD; currently ignored by the backend / 在 LCD 本地显示，Backend 当前不使用 |

Example message / 消息示例：

```json
{
  "sequence_number": 1,
  "temperature": 25.0,
  "humidity": 55.0
}
```

Only `temperature` is required. The optional `humidity` value does not currently change any actuator behavior.

只有 `temperature` 是必需字段。可选的 `humidity` 当前不会影响任何执行器行为。

### 2.2 Light sensor / 光线传感器

| Item / 项目 | Description / 说明 |
|---|---|
| Hardware / 硬件 | Grove Light Sensor (P) v1.0 |
| Interface / 接口 | GrovePi+ A0 |
| MQTT topic | `garage/sensor/light` |
| Backend field / Backend 字段 | `lux` |
| Current use / 当前用途 | Garage-light planning / 车库照明规划 |

Example message / 消息示例：

```json
{
  "sequence_number": 1,
  "lux": 350.0
}
```

The physical sensor currently produces a raw ADC value from 0 to 1023. It is temporarily stored in the `lux` field, but it is not yet calibrated as real lux.

当前物理传感器输出 0–1023 的原始 ADC 数值。该数值暂时存储在 `lux` 字段中，但还没有校准为真实的照度单位 lux。

### 2.3 Parking occupancy input / 停车位占用输入

| Item / 项目 | Description / 说明 |
|---|---|
| Current source / 当前来源 | D4 button simulation or another parking sensor / D4 按钮模拟或其他停车传感器 |
| MQTT topic | `garage/sensor/parking` |
| Parking positions / 停车位 | `0`, `1`, and `2` |
| Backend fields / Backend 字段 | `position`, `on_occupy` |
| Current use / 当前用途 | Determine whether the garage is full / 判断车库是否已满 |

Example message / 消息示例：

```json
{
  "sequence_number": 1,
  "position": 0,
  "on_occupy": true
}
```

The garage is considered full only when all three configured positions are occupied.

只有当三个配置的停车位都被占用时，系统才认为车库已满。

### 2.4 Vehicle-entry event / 车辆进入事件

| Item / 项目 | Description / 说明 |
|---|---|
| Source / 来源 | Camera and license-plate recognition software / 摄像头和车牌识别软件 |
| MQTT topic | `garage/camera/vehicle_entry` |
| Backend fields / Backend 字段 | `license_plate`, `enter_time` |
| Current use / 当前用途 | Register the vehicle and request entrance-gate opening / 登记车辆并请求打开入口门闸 |

Example message / 消息示例：

```json
{
  "sequence_number": 1,
  "license_plate": "TEST001",
  "enter_time": "2026-07-15T14:30:00"
}
```

### 2.5 Vehicle-exit event / 车辆离开事件

| Item / 项目 | Description / 说明 |
|---|---|
| Source / 来源 | Camera and license-plate recognition software / 摄像头和车牌识别软件 |
| MQTT topic | `garage/camera/vehicle_exit` |
| Backend field / Backend 字段 | `license_plate` |
| Current use / 当前用途 | Remove the vehicle record and request exit-gate opening / 删除车辆记录并请求打开出口门闸 |

Example message / 消息示例：

```json
{
  "sequence_number": 1,
  "license_plate": "TEST001"
}
```

If the license plate is not present in the current vehicle records, the backend logs a warning but continues running.

如果车牌不在当前车辆记录中，Backend 会记录警告，但不会退出程序。

---

## 3. Backend Internal State / Backend 内部状态

The backend stores the current garage state in the `Context` object.

Backend 使用 `Context` 对象保存当前车库状态。

### 3.1 Sensor and event state / 传感器与事件状态

| Context field | Type / 类型 | Meaning / 含义 | Initial value / 初始值 |
|---|---|---|---|
| `temperature` | `float \| None` | Current temperature / 当前温度 | `None` |
| `lux` | `float \| None` | Current light reading / 当前光线读数 | `None` |
| `positions_occupied` | `list[bool]` | Occupancy of positions 0–2 / 0–2 号停车位占用状态 | `[False, False, False]` |
| `current_vehicles` | `dict[str, str]` | License plate to entry-time records / 车牌到进入时间的记录 | `{}` |
| `vehicle_waiting_to_enter` | `bool` | A vehicle currently requests entry / 当前有车辆请求进入 | `False` |
| `vehicle_waiting_to_leave` | `bool` | A vehicle currently requests exit / 当前有车辆请求离开 | `False` |
| `garage_size` | `int` | Number of configured positions / 配置的停车位数量 | `3` |

### 3.2 Actuator state / 执行器状态

| Context field | Meaning / 含义 | Initial value / 初始值 |
|---|---|---|
| `fan` | Fan is on / 风扇已开启 | `False` |
| `light` | Garage light is on / 车库灯已开启 | `False` |
| `entrance_gate` | Entrance gate is open / 入口门闸已打开 | `False` |
| `exit_gate` | Exit gate is open / 出口门闸已打开 | `False` |

Because the current hardware protocol has no actuator acknowledgement topic, the backend updates actuator state optimistically after a command is accepted for MQTT publishing.

由于当前硬件协议没有执行器确认消息 Topic，Backend 会在命令被 MQTT 接受发布后，乐观地更新执行器状态。

---

## 4. Derived Planning State / 规划使用的派生状态

The PDDL problem generator converts Context values into planning predicates.

PDDL Problem Generator 会把 Context 中的值转换成规划谓词。

| Planning predicate / 规划谓词 | Becomes true when / 何时为真 |
|---|---|
| `temperature-high` | `temperature >= 30.0 °C` |
| `lux-dark` | `lux <= 100.0` |
| `garage-full` | All three parking positions are occupied / 三个停车位全部被占用 |
| `vehicle-waiting-to-enter` | A valid vehicle-entry event has been received / 收到有效的车辆进入事件 |
| `vehicle-waiting-to-leave` | A valid vehicle-exit event has been received / 收到有效的车辆离开事件 |
| `fan-on` | Context records the fan as on / Context 记录风扇已开启 |
| `light-on` | Context records the light as on / Context 记录车库灯已开启 |
| `entrance-gate-open` | Context records the entrance gate as open / Context 记录入口门闸已打开 |
| `exit-gate-open` | Context records the exit gate as open / Context 记录出口门闸已打开 |

The light threshold of `100.0` is provisional because the current A0 input is a raw ADC reading. It must be calibrated during physical testing.

光线阈值 `100.0` 目前是临时值，因为 A0 输入仍是原始 ADC 读数。该阈值需要在真实硬件测试中校准。

---

## 5. Actuators and Behavior / 执行器与行为

### 5.1 Fan / 风扇

| Item / 项目 | Description / 说明 |
|---|---|
| Hardware / 硬件 | Grove Relay controlling fan power / Grove Relay 控制风扇电源 |
| Interface / 接口 | D3 |
| MQTT topic | `garage/actuator/fan` |
| Commands / 命令 | `"on"`, `"off"` |

Behavior / 行为：

- If temperature is at least 30.0 °C and the fan is off, the planner produces `turn-on-fan`.
- 当温度大于或等于 30.0 °C 且风扇关闭时，Planner 生成 `turn-on-fan`。
- If temperature is below 30.0 °C and the fan is on, the planner produces `turn-off-fan`.
- 当温度低于 30.0 °C 且风扇开启时，Planner 生成 `turn-off-fan`。
- The Raspberry Pi maps `"on"` to D3 = 1 and `"off"` to D3 = 0.
- 树莓派把 `"on"` 映射为 D3 = 1，把 `"off"` 映射为 D3 = 0。

### 5.2 Garage light / 车库照明

| Item / 项目 | Description / 说明 |
|---|---|
| Hardware / 硬件 | Grove LED |
| Interface / 接口 | D8 |
| MQTT topic | `garage/actuator/light` |
| Commands / 命令 | `"on"`, `"off"` |

Behavior / 行为：

- If the light reading is at or below 100.0 and the light is off, the planner produces `turn-on-light`.
- 当光线读数小于或等于 100.0 且车库灯关闭时，Planner 生成 `turn-on-light`。
- If the reading is above 100.0 and the light is on, the planner produces `turn-off-light`.
- 当光线读数高于 100.0 且车库灯开启时，Planner 生成 `turn-off-light`。
- The Raspberry Pi maps `"on"` to D8 = 1 and `"off"` to D8 = 0.
- 树莓派把 `"on"` 映射为 D8 = 1，把 `"off"` 映射为 D8 = 0。

### 5.3 Entrance gate / 入口门闸

| Item / 项目 | Description / 说明 |
|---|---|
| Hardware / 硬件 | 9g servo |
| Interface / 接口 | GPIO18, physical pin 12 |
| MQTT topic | `garage/actuator/entrance` |
| Commands / 命令 | `"open"`, `"close"` |

Behavior / 行为：

- A valid vehicle-entry event sets `vehicle_waiting_to_enter = True`.
- 有效的车辆进入事件会把 `vehicle_waiting_to_enter` 设置为 `True`。
- If a vehicle is waiting, the garage is not full, and the gate is closed, the planner produces `open-entrance-gate`.
- 如果有车辆等待、车库未满并且入口门闸关闭，Planner 生成 `open-entrance-gate`。
- If the garage is full, no entrance-open action is generated.
- 如果车库已满，则不会生成打开入口门闸的动作。
- After the open command is published, the backend records the gate as open and clears the waiting flag.
- 打开命令发布后，Backend 记录门闸为打开状态，并清除车辆等待标志。
- On a later state-change event, an open gate with no waiting vehicle can produce `close-entrance-gate`.
- 在后续状态变化事件中，如果门闸处于打开状态且没有车辆等待，Planner 可以生成 `close-entrance-gate`。

### 5.4 Exit gate / 出口门闸

| Item / 项目 | Description / 说明 |
|---|---|
| Hardware / 硬件 | Not currently connected / 当前未连接 |
| Interface / 接口 | Reserved / 预留 |
| MQTT topic | `garage/actuator/exit` |
| Commands / 命令 | `"open"`, `"close"` |

Behavior / 行为：

- A valid vehicle-exit event sets `vehicle_waiting_to_leave = True`.
- 有效的车辆离开事件会把 `vehicle_waiting_to_leave` 设置为 `True`。
- If the exit gate is closed, the planner produces `open-exit-gate`.
- 如果出口门闸关闭，Planner 生成 `open-exit-gate`。
- After publishing the open command, the backend clears the waiting flag.
- 打开命令发布后，Backend 清除车辆等待标志。
- A later state-change event can produce `close-exit-gate`.
- 后续状态变化事件可以触发 `close-exit-gate`。
- The software topic and planning behavior are implemented, but physical exit-gate behavior cannot yet be verified.
- 软件 Topic 和规划行为已经实现，但当前还无法验证真实出口门闸动作。

### 5.5 LCD / LCD 状态显示

The I2C LCD is a local output device rather than a backend-controlled actuator. The Raspberry Pi displays temperature, humidity, light, fan, and gate status directly. There is no LCD MQTT command topic.

I2C LCD 是本地输出设备，而不是由 Backend 控制的执行器。树莓派会直接显示温度、湿度、光线、风扇和门闸状态，因此没有单独的 LCD MQTT 命令 Topic。

---

## 6. Behavior Summary / 行为汇总

| Input condition / 输入条件 | Planner action / 规划动作 | MQTT output / MQTT 输出 | Physical result / 硬件结果 |
|---|---|---|---|
| `temperature >= 30.0` and fan off / 且风扇关闭 | `turn-on-fan` | `fan -> "on"` | D3 relay activates fan / D3 Relay 启动风扇 |
| `temperature < 30.0` and fan on / 且风扇开启 | `turn-off-fan` | `fan -> "off"` | D3 relay stops fan / D3 Relay 关闭风扇 |
| `lux <= 100.0` and light off / 且车库灯关闭 | `turn-on-light` | `light -> "on"` | D8 LED turns on / D8 LED 点亮 |
| `lux > 100.0` and light on / 且车库灯开启 | `turn-off-light` | `light -> "off"` | D8 LED turns off / D8 LED 熄灭 |
| Entry request and free space / 有进入请求且存在空位 | `open-entrance-gate` | `entrance -> "open"` | GPIO18 servo opens gate / GPIO18 舵机开门 |
| Garage full / 车库已满 | No entrance-open action / 不生成开门动作 | None / 无 | Entrance stays closed / 入口保持关闭 |
| No entry request and entrance open / 无进入请求且入口已打开 | `close-entrance-gate` | `entrance -> "close"` | Servo closes gate / 舵机关门 |
| Exit request / 有离开请求 | `open-exit-gate` | `exit -> "open"` | Software output only currently / 当前只有软件输出 |

---

## 7. Current Limitations / 当前限制

- Humidity is not used by Context or the AI planner.
- 湿度目前不参与 Context 或 AI Planner。
- The A0 light reading is not calibrated as real lux.
- A0 光线读数尚未校准为真实 lux。
- D4 has not yet been finalized as either a parking simulator or a manual-control button.
- D4 尚未最终确定用于停车位模拟还是本地手动控制。
- Actuator state is optimistic because the Raspberry Pi does not publish acknowledgements.
- 由于树莓派没有发布执行器确认消息，Backend 中的执行器状态采用乐观更新。
- Entrance-gate closure occurs during a later state-change planning cycle, not through a dedicated timer.
- 入口门闸关闭发生在后续状态变化的规划周期中，目前没有独立定时器。
- Exit-gate hardware is not connected.
- 出口门闸硬件尚未连接。

---

## 8. Hardware Debug Dashboard and Camera API / 硬件调试页面与相机 API

Running `python3 main.py` starts the MQTT subscriber, MQTT publisher, planner,
camera API, and dashboard together. The dashboard is available at
<http://localhost:8080>.

运行 `python3 main.py` 会同时启动 MQTT Subscriber、MQTT Publisher、Planner、相机
API 和 Dashboard。网页地址为 <http://localhost:8080>。

| API | Behavior / 行为 |
|---|---|
| `GET /api/state` | Return Context, parking, recent input messages, and actuator commands / 返回 Context、停车位、最近输入消息和执行器命令 |
| `POST /api/camera/enter` | Start OCR and send a `vehicle_entry` event directly to the backend; rejected before camera startup when full / 启动 OCR 并把 `vehicle_entry` 事件直接交给 Backend；车库满时在启动相机前拒绝 |
| `POST /api/camera/exit` | Start OCR and send a `vehicle_exit` event directly to the backend; available even when full / 启动 OCR 并把 `vehicle_exit` 事件直接交给 Backend；车库满时仍可使用 |

Only one camera request can run at a time. A recognized plate is passed
directly to the backend and follows the Context → Planner → Actuator path.
Only the final actuator command is published through MQTT.

Camera capture started through the web API runs without an OpenCV desktop
preview window. This avoids macOS GUI-thread errors; the operator should hold
the plate steady while the dashboard displays the processing message.

同一时间只允许一个相机请求。识别出的车牌直接交给 Backend，并进入
Context → Planner → Actuator 流程。只有最终执行器命令通过 MQTT 发布。

通过 Web API 启动的相机采用无 OpenCV 桌面预览窗口的拍摄方式，以避免 macOS
GUI 线程错误。Dashboard 显示处理中提示时，操作人员应保持车牌稳定。

---

## 9. Related Documents / 相关文档

- [Hardware and backend interface / 硬件与 Backend 接口](../hardware_setting.md)
- [Hardware integration implementation plan / 硬件集成实施计划](../implementation.md)
- [MQTT message format / MQTT 消息格式](message_format.md)
