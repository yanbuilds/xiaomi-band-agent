# 本地隐私审计

每次提取日志、测试认证或制作固件候选包后，可以运行：

```powershell
powershell -ExecutionPolicy Bypass -File tools/privacy_audit.ps1
```

脚本只检查 Git 路径名和原始日志目录是否存在，不读取或打印密钥、MAC、DID、账户或日志内容。返回码为 0 才允许继续实验；发现被跟踪的敏感路径或原始日志目录时返回 2。

本地凭据文件可以存在于 `work/mihealth/credentials.local`，但必须保持被 `.gitignore` 忽略，且不能复制到 `outputs/`、提交、上传或粘贴到聊天中。

对需要复核协议轨迹的单个日志，可使用：

```powershell
python tools/audit_mifitness_markers.py work/mihealth-log-extract/XiaomiFit.device.log
```

它只输出文件名、大小、SHA-256、行数和预定义标记的行数，不输出日志内容。
