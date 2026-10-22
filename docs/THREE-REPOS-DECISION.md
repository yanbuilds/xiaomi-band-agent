# 三个仓库在 Band 9 Pro 项目中的边界

更新时间：2026-10-22

## 结论

三个仓库不能拼成一个“直接解锁 n67cn 固件”的现成方案，但可以组合成一条可落地的产品路线：

```text
Android bridge
  ├─ Gadgetbridge / Xiaomi protobuf / BLE V2
  ├─ FreeBand 的 auth、活动文件和解析思路
  ├─ 本地 API → Grok bot → 通知与震动
  └─ ATC1441 SDK 仅用于独立的 BES2700iMP 串口实验
```

## 仓库评估

| 仓库 | 已验证价值 | 对 n67cn 的直接帮助 | 不能替代的部分 |
|---|---|---|---|
| [Gadgetbridge](https://codeberg.org/Freeyourgadget/Gadgetbridge) | Xiaomi protobuf、认证、BLE/SPP、`XiaomiNotificationService` | 最高；应作为 Android bridge 的协议底座 | 不包含 n67cn 私钥，也不绕过固件签名 |
| [miband-mcp](https://github.com/kirisawa-subaru/miband-mcp) | USB/ADB、Gadgetbridge 数据导出、MCP 和 agent 配置 | 可直接复用数据编排与 Agent 接口 | 当前公开验收范围是 Band 10 + Android + Gadgetbridge + Linux/macOS；不是刷机工具 |
| [ATC1441/BES2700iMP](https://github.com/atc1441/MiBand10-BES2700iMP-BEST1503-Hacking) | BEST1503 SDK、串口烧录器、Mi Band 10 硬件 bring-up | 可用来研究同 SoC 的启动、显示和 UART 工具链 | 作者明确写明只在 Band 10 测试；9 Pro 的测试点、分区和显示参数仍未证实 |
| [FreeBand](https://github.com/cobanov/freeband) | BLE V2、HKDF/HMAC、AES-CTR、活动文件和通知/震动能力 | 可把 iOS 逆向结果迁移到 Android bridge | Band 10/10 Pro 的实测不能自动证明 n67cn 9 Pro 兼容 |

## 为什么现在不能提交“可刷入的自制包”

本仓库已从官方 n67cn 3.1.175、3.1.190 全量包和 3.1.175→3.1.190 增量包中复现外层尾部校验：

* 最后 ZIP EOCD 后固定有 268 字节尾部；其中 256 字节是 RSA-2048 PKCS#1 v1.5/SHA-256 签名。
* 签名消息是 `image[:final_zip_eocd_end] + trailer[:8]`。
* 三个官方包都能用 `work/firmware-lab/n67cn_public.pem` 验证；修改资源后签名立即失败。
* 这和 OpenVela 公布的 APK Sig Block/AVB 机制不同，不能拿公开 demo key 替换。

因此，ATC SDK 可以帮助我们做“独立串口实验固件”，但不能把它包装成 OTA 发送给当前 n67cn 设备。除非找到以下任一新证据，否则不能安全地称它为可刷包：

1. Xiaomi n67cn 的签名私钥或官方签名服务；
2. 经过实机确认的 bootloader/UART 路径，并证明该路径允许关闭或绕过签名；
3. 可恢复的低级调试入口（SWD/JTAG/ROM 下载模式）以及完整的 n67cn 分区和启动链证据。

## 当前实现选择

1. 先用 Gadgetbridge/FreeBand 路径完成数据同步、Grok 分析、通知和震动；这不需要刷机。
2. 把 ATC1441 代码保持在独立实验分支，先通过 n67cn 真机只读 UART 探测确认 SoC、分区和测试点。
3. 所有 OTA 候选都必须经过 `tools/ota_preflight.py --public-key work/firmware-lab/n67cn_public.pem`；签名失败的包只作为负控样本，禁止发送。

## 可复核命令

```powershell
python tools/verify_n67cn_outer_signature.py `
  work/firmware-lab/n67cn_v3.1.190_full.bin `
  --public-key work/firmware-lab/n67cn_public.pem

python tools/ota_preflight.py `
  outputs/band9pro-mvp/n67cn-v3.1.190-font-incremental-signed-shape.bin `
  --public-key work/firmware-lab/n67cn_public.pem
```

第一条应报告 `signature_verified: true`；第二条应明确拒绝发送。这是当前“能解析”与“设备会接受”之间的硬边界。
