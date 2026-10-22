# n67cn 被动 UART/USB 启动采集

这份流程只用于确认接口，不向手环发送字节，也不执行擦除、写入或复位。

## 设备要求

- 已拆下外壳、断开电池后再拍摄主板正反面高清照片；不要在通电状态下短接未知焊盘。
- 3.3 V 逻辑分析仪或 USB-UART，输入端高阻、禁止自动发送；严禁 5 V 电平。
- 电源使用带限流的实验电源，先限制在 50 mA 以下；不使用磁吸充电线当作调试接口。
- 先保存照片、芯片丝印、焊盘坐标和接地位置，不要刮漆或焊接。

## 监听顺序

1. 断电连接 GND 和逻辑分析仪 RX；TX 保持悬空。
2. 只在确认电平不超过 3.3 V 后上电，记录 30 秒原始波形。
3. 依次离线解码 115200、921600、1.5M baud；常见 8-N-1，不能为了“试试”发送同步字节。
4. 搜索 `NuttShell`、`NSH`、`bl2>`、`SecureBoot`、`sign verify` 等只读 banner。
5. 将原始捕获保存到本地 `work/uart/`，提交前只保留脱敏后的 baud、时间戳和 banner 摘要。

仓库已有的监听器会拒绝写入模式。`n67cn_readonly_uart_probe.py` 还会默认
dry-run；因为上游探针会把 SecondStage 程序加载到 RAM，只有明确理解这点并
确认使用独立测试板时，才可添加 `--execute-read-only`。这不是被动监听：
它会发送同步/加载字节，但仍不传递 `--write`、不擦除非易失存储。

```powershell
python tools/n67cn_uart_listen.py --port COM7 --baud 115200 --seconds 30 `
  --output work/uart/bl2-115200.log
```

对上游 BES 读模式的预演：

```powershell
python tools/n67cn_readonly_uart_probe.py --port COM7 `
  --flasher work/atc-bes-hacking/bes2700impForDisplayRe/flasher/bes2700_flasher.py `
  --output work/uart/n67cn-read.bin
```

上面命令只打印命令，不发送 UART；只有在专用测试板和恢复方案就绪后，才
显式增加 `--execute-read-only`。

只有在捕获到明确的 BL2 提示符、完成整片只读备份并准备好恢复路径后，才有理由研究命令协议。AP 的 `AT^...` 字符串不能替代这个条件；它们不在 BL2 或 OTA loader 中。

## 隐私处理

- 不上传原始串口日志、序列号、MAC、DID、密钥或账户信息。
- 报告中只写芯片型号、波特率、banner 类别和哈希；日志文件留在本机并加入忽略列表。
- 任何写入实验必须另建明确的备份和恢复记录，不能在日常佩戴的唯一设备上进行。
