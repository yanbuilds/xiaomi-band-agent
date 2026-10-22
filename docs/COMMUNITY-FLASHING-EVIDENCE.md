# 社区刷机证据边界

目前公开资料能证明的是官方包的传输与版本选择，不是自定义包的签名绕过：

- [BandBBS 固件库说明](https://www.bandbbs.cn/resources/7772/) 将
  `miwear.watch.n67cn` 映射为小米手环 9 Pro，并明确区分 full 包和带
  `from_vX` 的 incremental 包；增量包有严格源版本依赖。
- [firmware-archives-public](https://github.com/hrk666666/firmware-archives-public)
  保存官方发布的 n67cn 包，适合做基线和恢复包。
- [Sany18/smart-band](https://github.com/Sany18/smart-band) 的 n67cn 笔记明确把
  Gadgetbridge、RPK 和官方固件转换分开；它没有提供绕过 Xiaomi OTA 签名的方案。
- 社区里出现过通过 Notify/Mi Fitness 替换官方下载文件来转换全球固件的教程，
  但这仍然使用厂商签名包，不能证明任意修改的 AP/资源包会被接受。

因此本项目的 `font-rebuilt` 和 `font-incremental-fullset` 只能标为“结构完整的
自定义候选包”。只有在 n67cn 真机上通过 `PrepareOta`、签名校验、重启和功能回归后，
才能升级为“可刷入包”。在此之前，官方 3.1.190 包仍是唯一可作为恢复基线的包。

## 2026-10-22 再核查

ATC1441 项目的 [Band 9 Pro UART issue](https://github.com/atc1441/MiBand10-BES2700iMP-BEST1503-Hacking/issues/4)
仍处于 open 状态，没有针脚照片、启动日志或作者确认。因此目前没有新的
9 Pro 低级刷写证据可用于修改这条结论。

独立的 [wrist-tarot RPK 项目](https://github.com/yansheng1014/wrist-tarot)
确认 Band 9 Pro 的公开 Vela 快应用构建目标（336 宽度、`.rpk` 产物），但它同样
不是 AP/bootloader 固件，也不提供签名绕过。
