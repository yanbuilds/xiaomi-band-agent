# HyperionD/minstall 评估

仓库：[HyperionD/minstall](https://github.com/HyperionD/minstall)。本地审计基于提交
`56f74ec`，只读检查了 Python POC、Rust 协议层和 Android 连接层。

## 结论

它对本项目**有用，但不是 Band 9 Pro 固件刷机工具**。它提供了一条已经实现的
Android 经典蓝牙 RFCOMM/SPP 路线，可直接复用到“安装 RPK 快应用”和后续控制面
实验；仓库 README 明确写的是 Band 10 Pro 已验证协议，不能把它当成 n67cn/3.1.175
已验证实现。

## 能复用的部分

- Android `BluetoothSocket` + RFCOMM channel 5 字节流桥接到 Rust；这比在手机上
  重新实现一套 BLE GATT 传输更接近公开的 Band 10 Pro 实测路径。
- 16 字节 authkey 的格式校验、官方 `wearablelog/*.zip` 中 `encryptKey`/`token`
  候选提取、Android Keystore 加密保存。提取结果必须在用户设备上确认，不能把日志
  或密钥上传到服务器。
- V2 帧、CRC16、protobuf、AES-128-CTR、HMAC 认证，以及 `START_SESSION` 握手。
- Vela RPK 的 `ThirdpartyApp` 安装请求、`Mass PREPARE`、data type 64 分片传输、
  安装结果/已安装列表查询。该流程和我们现有的 `band-agent-debug.rpk` 控制面
  目标高度匹配。

## 不能据此宣称的能力

- 没有 n67cn 或 Band 9 Pro 的型号判断、固件 3.1.175 回归记录；源码中的扫描器和
  README 都把目标写成 Band 10 Pro。
- 没有 AP/BL 固件签名私钥、Boot ROM 解锁、UART 测试点或任意固件刷写能力。
  `MASS` 只是已被固件接受的第三方应用/表盘传输通道。
- 没有健康数据同步协议实现，也没有通知/震动 API 的 Band 9 Pro 兼容性证明。

## 与本项目的落地方式

```text
Android Bridge (authkey + RFCOMM/SPP)
        ├── V2 auth/session
        ├── RPK installer  -> band-agent-debug.rpk
        └── future: health/notification commands (需 n67cn 实机抓包)
                         │
                         └── @system.interconnect -> RPK UI/vibrator
```

下一步应把 `minstall` 的 Rust 协议层作为参考或独立 adapter，先做三项低风险验收：

1. 在**解锁手机**上安装构建产物，确认能发现并连接 `miwear.watch.n67cn`；
2. 仅执行 V2 `START_SESSION` 和设备信息读取，确认 authkey/型号，不发送 MASS；
3. 备份现有 RPK 后再尝试安装我们的 debug RPK，失败时保留日志摘要，不上传密钥。

只有第 1、2 项通过后，才值得把 RPK 安装命令接入 `PhoneSyncCoordinator`。真实健康
数据和通知仍优先走现有 Gadgetbridge fork；minstall 目前只能补齐“手机直连 + RPK
安装”这一段。

## 许可证和安全边界

仓库标注 MIT，可作为协议参考或在保留版权声明的前提下复用小段代码。不要复制用户
导出的 authkey、完整 wearablelog、蓝牙地址或带身份信息的抓包到 GitHub；不要在
未验证 n67cn 响应前启用自动 MASS/刷写按钮。
