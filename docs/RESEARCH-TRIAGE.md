# 三个外部项目的分工

## Gadgetbridge

这是 Android 侧的底座：配对、认证、Xiaomi protobuf、活动文件、通知和
RPK/`@system.interconnect` 通道都在这里。我们使用的 CN Band 9 Pro 代码基线
来自 Gadgetbridge 的设备服务和 Sany18 的 RPK 分支。它是 AGPL 项目，若把修改
合入发布版，必须保留许可证和对应源码。

## miband-mcp

这是 Agent 侧很有价值的“数据库/同步适配层”，不是新的手环无线协议实现。它
通过 Gadgetbridge 的授权 ADB、数据库导出和 SQLite 缓存，把最近状态、日报、睡眠、
心率和活动记录暴露为 MCP 工具。它当前的实测范围主要是国内版 Android + Band 10，
电脑端支持 Linux/macOS，Windows 尚未验收；因此不能直接宣称已支持 Band 9 Pro。

我们应该复用它的接口思想和数据新鲜度/归档设计，把我们的 Grok webhook 接在
`sync_health → 本地归档 → Agent → 通知 outbox` 之后；不要让 Grok 直接接触
蓝牙密钥或手环链路。

## MiBand10-BES2700iMP-BEST1503-Hacking

这是固件和刷写层的底座：BEST1503 HAL、显示/触摸初始化、UART BESLink、
SecondStage programmer。它声称 Band 9/10 共享 SoC，但实际自定义固件仍主要在
Band 10 上验证。对我们的 `n67cn` 样本，已验证相同 Vela 启动头和 Thumb 代码，
但尚未验证主板测试点、Flash 分区、签名策略和恢复流程。

## 对本项目的结论

| 目标 | 首选来源 | 当前状态 |
|---|---|---|
| 本地健康数据 | Gadgetbridge + miband-mcp 的归档/查询设计 | 可整合，Band 9 Pro 仍需真机回归 |
| Grok 交互 | 我们的 RPK + Gadgetbridge `XiaomiRpkService` | 已构建 RPK，未做设备验收 |
| 真正刷写自定义固件 | BEST1503 SDK + n67cn 启动块 | 已有结构证据，尚未生成可验证刷写包 |

来源：[Gadgetbridge](https://codeberg.org/Freeyourgadget/Gadgetbridge)、
[miband-mcp](https://github.com/kirisawa-subaru/miband-mcp)、
[BEST1503 hacking](https://github.com/atc1441/MiBand10-BES2700iMP-BEST1503-Hacking)。

## Sany18/smart-band（独立 n67cn 交叉证据）

该项目的公开说明把 `n67cn` 与 `n67gl` 的固件型号检查列为未解决问题，没有给出跨区刷写或签名绕过；同时记录了 Band 9 Pro 的 RPK 快应用路线，并指出 RPK 包里的 `CERT` 在实际安装链路中不是固件级厂商签名。它还提供 Vela/aiot-toolkit 模拟器和 quick-app 开发资料。这个结果与本仓库的签名审计一致：RPK 是可继续推进的控制面，不能当作 AP/BL 固件刷写能力。

来源：[Sany18/smart-band](https://github.com/Sany18/smart-band)。

## 公开资料复核（2026-10-23）

对 Sany18/smart-band 的当前公开说明再次核对后，结论没有变化：它明确写出
`n67cn` 到 `n67gl` 的机型检查仍没有已知绕过，并把 RPK 快应用列为实际可用的
控制面；它没有提供 Band 9 Pro 的 Boot-ROM 解锁、厂商签名私钥或可验证的 UART
测试点。该项目还提醒不要把 RPK 的 `CERT`/`hash.json` 当作固件签名。这个交叉
证据支持继续完善 RPK + Android 中转，而不把未验证的 BEST1503 flasher 直接用于
`n67cn` 主板。

截至 2026-10-23，ATC 项目的公开 issue「UART pads on Mi Band 9 Pro」仍处于
Open 状态，没有维护者回复、附件、分支或可复现的 n67cn 测试点记录。因此该 issue
仍不能作为刷写依据；仓库中的示意 Pinout 不能直接套用到本手环。
