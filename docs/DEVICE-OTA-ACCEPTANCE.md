# n67cn OTA 真机验收步骤

这份步骤用于确认 `n67cn` 是否接受资源实验包。它要求 Android 手机连接
ADB，并且手环当前版本为 `3.1.175`。没有实体设备日志时，离线校验不能替代
下面的验收。

## 0. 安全门

- 先导出 Gadgetbridge 配对密钥和设备信息，保留官方 Mi Fitness 作为恢复路径。
- 电量至少 60%，关闭省电和蓝牙自动切换；测试期间不要解绑手环。
- 先验证官方包，官方包没有成功前不得发送候选包。
- 保留官方增量包的原始 SHA-256：
  `360cb9c46b3df3170d44fab8216996d2f53d7c14226d254027a485cf6aecbc7f`。

## 1. 构建和安装 Gadgetbridge

在 Sany18 Gadgetbridge fork 应用
`android-bridge/patches/gadgetbridge-n67cn-firmware-header.patch`，再运行：

```powershell
./gradlew :app:assembleMainlineDebug --no-daemon --no-parallel --max-workers=1
adb install -r app/build/outputs/apk/mainlineDebug/app-mainline-debug.apk
```

如果使用带 RPK interconnect 的分支，保留该分支的 `XiaomiRpkService` 修改；固件
头补丁只负责让 n67cn 文件进入现有 OTA 上传路径。

## 2. 第一阶段：官方包

选择官方 `3.1.190_from_3.1.175` 包，记录日志并等待设备完成重启。必须看到：

1. `PrepareOta` 返回 `READY`；
2. MASS 类型为 `0x20`，MD5 与文件一致；
3. 分片发送完成；
4. 手环重启后版本变为 `3.1.190`，健康数据和蓝牙连接正常。

任一项失败都停止测试，恢复官方连接，不发送自定义包。

发送官方包前可先做离线签名基线：

```powershell
python tools/ota_preflight.py `
  work/firmware-lab/n67cn_v3.1.190_from_v3.1.175.bin `
  --current-version 3.1.175 `
  --public-key work/firmware-lab/n67cn_public.pem
```

该命令会验证官方 268 字节 RSA 尾部；必须得到
`signature_verified: true` 才进入发送阶段。

## 3. 第二阶段：资源候选包

从 3.1.175 设备开始，若需要验证设备端拒绝路径，可测试以下保留签名尾部
形状但签名必然失效的负控制文件：

`outputs/band9pro-mvp/n67cn-v3.1.190-font-incremental-signed-shape.bin`

发送前核对：

```text
size = 8270038
sha256 = a571555940d02755699a616ef8bc09b21b102f52a65c93f2fb4aa803c26a2741
mode = 2
target version = 3.1.190
```

发送前执行带公钥的 preflight；它应当拒绝该文件，因为
`signature_verified` 为 `false`。不要把“结构有效”解释为“可以刷入”。

验收重点是设备返回的安装结果，而不是手机端“上传完成”：

- `PrepareOta` 是否为 `READY`；
- 是否在签名/校验阶段拒绝；
- 是否重启并回到系统；
- 重启后字体资源是否变化、健康数据是否仍可同步；
- 若失败，记录最后一条 `PrepareOta`、MASS 和系统状态 protobuf，再恢复官方包。

## 4. 结果解释

- 官方包成功、候选包在签名阶段失败：说明容器和传输正确，但资源也被签名覆盖，
  不能靠 ZIP CRC 修改绕过。
- 候选包成功并重启：才可以把它称为“已验证可刷入的资源固件包”；随后再做更小
  的功能性资源实验。
- 两者都失败：先修复 Gadgetbridge 认证、版本字段或上传链路，不能归因于候选包。

这份验收不会修改启动区，也不会尝试擦除 Flash；任何 bootloader/AP 改写都必须另有
可恢复的 UART/SecondStage 路径和完整备份。

## 离线基线

可以用总审计工具在发送前强制检查外层 RSA 签名：

```powershell
python tools/flashability_audit.py <candidate.bin> \
  --public-key work/firmware-lab/n67cn_public.pem
```

只有输出 `flashable: true` 才表示候选满足本地签名门；输出
`flashable: false` 的候选即使 ZIP/CRC 正确，也必须禁止写入设备。该工具
始终标记 `device_write_attempted: false`，不会连接、重启或发送任何数据。

完整镜像资源实验版也保存在实验目录中：

```text
work/firmware-lab/n67cn_v3.1.190_font-rebuilt.bin
size   = 50330500
sha256 = 6941be39567efba5f7a123f58ea21b9e2b35ad95b30bf0870df2d0246663a63b
```

相对官方 `3.1.190_full.bin`，该文件只改变一个同尺寸归档：
`MiSansF-Demibold.ttf`，归档大小仍为 14,167 字节，CRC 从
`61f7c4b3` 变为 `9b07acd4`。`tools/validate_resource_candidate.py` 已报告
`errors: []`。这证明了可重复的资源级修改基线，但不证明设备会接受厂商签名。

增量候选也已从官方增量基线重新构建并得到相同 SHA-256：

```powershell
python tools/append_incremental_archive.py `
  work/firmware-lab/n67cn_v3.1.190_from_v3.1.175.bin `
  work/firmware-lab/n67cn_v3.1.190_font-rebuilt.bin `
  --source-start 0x2ffc321 `
  --output work/firmware-lab/rebuilt-fullset.bin
```

旧版不带尾部形状的重建结果仍保存在
`outputs/band9pro-mvp/n67cn-v3.1.190-font-incremental-fullset.bin`，其 SHA-256
为 `6831f9951c1ab184a43eb39b5fe2af9dacbc983462848a8253037aae11adf6fd`。
新版负控制候选保留了 268 字节尾部，但 RSA 签名明确无效；这两个文件都不应
被标记为已验证可刷入。

The full-set incremental candidate was run through OTA preflight from the
current 3.1.175 version. Container, MD5, SHA-256, and version ordering all pass,
but RSA verification fails (`ValueError`), so `send_allowed_by_preflight=false`.
The safety gate therefore refuses the candidate before any device write.

## 2026-10-23 离线复核

重新运行 `tools/validate_n67cn_hardware.py` 后，官方 AP 中的 NAND 证据仍完整：
`gd5f2gm7` 型号、读/写页、擦除块和容量查询标记均存在。对官方
`3.1.190_from_3.1.175` 增量包重新执行 `tools/ota_preflight.py`，结果为：
容器有效、版本从 `3.1.175` 升到 `3.1.190`、外层 RSA 签名验证通过，
`send_allowed_by_preflight=true`。这只证明官方增量包满足本地安全门；本轮没有
向手机或手环发送 OTA 数据。

## 手机侧官方包交叉校验（只读）

通过已连接的 ADB 设备只读检查 Mi Fitness 的下载目录，发现官方增量包已由应用
缓存到 `miwear.watch.n67cn` 目录。未复制该文件、未读取日志内容，也未触碰认证
字段；仅取得文件大小和摘要。设备侧文件大小为 `8,255,867` 字节，MD5 为
`f5ddb3030b984db91ff329989d3ad2c2`，SHA-256 为
`360cb9c46b3df3170d44fab8216996d2f53d7c14226d254027a485cf6aecbc7f`，与本地
官方增量包完全一致。这证明手机实际使用的 OTA 文件就是我们离线验证过的官方
文件；没有因此触发升级或写入操作。
