# 三个上游仓库评估（Band 9 Pro CN / 3.1.175）

## 结论

| 仓库 | 能直接解决什么 | 对 n67cn 的价值 | 当前结论 |
|---|---|---|---|
| [Gadgetbridge](https://codeberg.org/Freeyourgadget/Gadgetbridge) | Android BLE 认证、Xiaomi protobuf、历史数据同步、通知/震动、OTA 传输 | 最高；已有 n67cn 解析补丁和 XiaomiNotificationService 路线 | **主线实现** |
| [miband-mcp](https://github.com/kirisawa-subaru/miband-mcp) | 把 Gadgetbridge 数据库/手机同步暴露给 MCP Agent | 适合作为 Grok/本地 Agent 的数据接口，不负责破解或刷写手环 | **数据与 Agent 层复用** |
| [MiBand10-BES2700iMP-BEST1503-Hacking](https://github.com/atc1441/MiBand10-BES2700iMP-BEST1503-Hacking) | BEST1503 裸机 SDK、显示/触摸、UART flasher、可启动自定义固件 | 证明芯片级控制和有线烧录可行；只在 Mi Band 10 真机验证，不能直接当 n67cn 刷机包 | **实验性固件路线** |

## 1. Gadgetbridge

上游项目本身是本路线的协议实现来源；本地分支已经验证 `XiaomiNotificationService`、`XiaomiRpkService`、健康数据服务和 OTA 安装器可编译。它的职责边界是手机 BLE 中转和官方协议交互，不是修改手环 SoC 的裸机固件。

本地 Sany18 分支已经包含 Xiaomi 的完整服务拆分：`XiaomiHealthService`、活动文件解析、`XiaomiNotificationService`、`XiaomiRpkService` 和固件安装处理。通知路径是 protobuf `Command.type=7`，发送子类型为 `0`；通知体包含标题、正文、应用包名、时间戳和可选的手机打开键。手环回传的 dismiss/open/call-reply 命令也已有处理代码。

这条路径能实现：

1. Android 手机作为 BLE 中转，直接同步睡眠、心率、步数、血氧等记录；
2. Grok 返回文本后由手机发送通知并触发手环的常规通知震动；
3. 在协议已有字段范围内处理通知关闭、打开手机和部分预设回复。

它不能凭空增加官方固件没有的“任意可点击按钮”或语音输入 UI；这需要手环端 RPK/系统应用支持，或改写并签名整个固件。

当前仓库的 `android-bridge/patches/gadgetbridge-n67cn-firmware-header.patch` 只放宽了 n67cn 外层 OTA 头解析，Java 编译已通过。它没有绕过 RSA 签名，也没有修改写入分区逻辑。

## 2. miband-mcp

上游 README 当前把项目定位为健康数据 MCP，并明确公开验收路线是“国内 Android 手机 + Gadgetbridge + USB + Linux/macOS 电脑”；README 还明确写出目前公开支持目标是 Mi Band 10，Windows 尚未适配。因此它可以作为 Grok 的数据工具层，但不能被当作 Band 9 Pro 驱动、认证实现或刷机工具。

这个仓库的公开目标是“让 Agent 读取手环健康记录”。它的主验证路线是国内 Android + Gadgetbridge + USB + Linux/macOS 电脑；README 明确写出当前只对 Mi Band 10 做公开测试，并且 Windows 还未适配。它提供两个后端：

- `gadgetbridge`：通过 ADB 导出数据库，读取历史健康数据；
- `xiaomi_health`：依赖已有 root/SSH 的小米运动健康内部数据，属于实验路线。

因此它最适合直接拿来做 **Grok 的本地数据工具层**：同步后的 SQLite → MCP tool → Grok 分析 → 手机桥接层发通知。需要补上的工作是 n67cn 的设备测试、Windows/Android 后台保活，以及一个向 `XiaomiNotificationService` 或 RPK interconnect 发消息的反向工具。它不是 BLE 认证库，也不是固件刷写器。

## 3. atc1441 BES2700/BEST1503 Hacking

该仓库 README 明确写出：Mi Band 9 和 Mi Band 10 都使用 BES2700iMP/BEST1503，但仓库中的实现“只在 Mi Band 10 开发和测试”。它提供的是 BEST1503 裸机 SDK、显示/触摸重建和 UART SecondStage 刷写路径；这证明芯片级自定义固件在同系列设备上可行，却没有证明 Smart Band 9 Pro 的板级引脚、NAND 分区、显示时序和签名链相同。

仓库 README 的总览以 Mi Band 10 为主，但当前树里已经加入了一个名为 `bes2700impForDisplayRe` 的 **Mi Band 9（普通版）固件基座**，以及标注为“来自真实 Mi Band 9 UART 抓包”的 BES flasher。该基座的显示参数约为 192×490，BLE/传感器/OTA 仍有明确的 scaffold 或 TODO；它不是 Xiaomi Smart Band 9 Pro 的已验证移植。README 仍然明确提醒刷写会替换原厂固件，可能永久变砖。

对本项目有价值的部分：

- BEST1503 的启动、链接脚本、显示/触摸寄存器和 UART flasher 研究资料；
- 说明“芯片级自定义固件”不是理论上不可能；
- 可用于比对 n67cn `vela_ap.bin` 的启动头、内存布局和外设调用。

不能直接复用的部分：

- n67cn Pro 的分区、外层 OTA、签名、公钥和恢复流程；
- Mi Band 9 Pro 的屏幕/触摸板料号、GPIO、PSRAM 和电源时序（仓库基座写的是普通 Band 9 的约 192×490 面板）；
- 官方系统的 BLE 协议服务、健康数据任务和升级回滚逻辑。

所以当前不应把该仓库生成的 `best1503.bin` 送入 n67cn OTA。若要走芯片级路线，必须先取得 n67cn 主板测试点和完整 SPI flash 备份，再单独恢复 n67cn 的启动链和硬件参数；这属于高风险硬件实验，不是当前 MVP 的刷机步骤。

## 推荐组合

```text
Band 9 Pro CN
   │ BLE / Xiaomi auth
   ▼
Gadgetbridge fork（健康同步 + 通知/震动 + 可选 RPK）
   │ SQLite/JSON + 本地 HTTP
   ▼
miband-mcp 适配层
   │ MCP/Webhook
   ▼
Grok bot（睡眠分析、建议选项）
   │ text + action id
   ▼
手机桥接层 → XiaomiNotificationService 或 RPK interconnect → 手环
```

刷机研究单独放在旁路实验室：先做静态对比和 UART/测试点识别，等有完整备份与可恢复方案后再考虑 n67cn 自定义 AP/bootloader。通知、震动、文本回复和 RPK 交互不应等待刷机路线完成。

## 对“完全解锁”的判断

目前没有这三个仓库共同证明“Band 9 Pro CN 3.1.175 可以安全刷入任意自定义完整固件”。能证明的是：

1. 官方 BLE 协议和 Gadgetbridge 路线可做本地同步、通知和震动；
2. RPK interconnect 在 CN Band 9 Pro 上已有独立实机证据，可作为交互实验入口；
3. BEST1503 芯片级自定义固件在 Mi Band 10 上已经跑通，但 n67cn 仍缺真机硬件验证、备份和恢复链。

