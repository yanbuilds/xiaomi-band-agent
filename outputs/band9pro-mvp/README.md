# Band 9 Pro：本地同步 MVP 起点

可直接安装的 Vela 快应用在仓库的
[`band-agent-debug.rpk`](band-agent-debug.rpk)。它通过
`@system.interconnect` 接收 Grok 问题、触发 `@system.vibrator`、显示最多
三个选项，并把点击结果回传 Android。构建源码见
[`band-app/`](../../band-app/)，协议和安装说明见
[`docs/QUICKAPP-ROUTE.md`](../../docs/QUICKAPP-ROUTE.md)。

交付范围：可运行的离线睡眠 v2 解析器、SQLite/FastAPI 单用户后端、自动化测试、
带 HMAC 防重放的 Grok/Webhook 适配器、Android Worker 编排边界，以及 RPK 和
Gadgetbridge 适配源。`PhoneSyncCoordinator.kt` 由实际 Android 应用提供 HTTP
实现后即可放进 WorkManager；它不会创建第二条蓝牙连接。Grok bot 通过通用 API
接入，无须把蓝牙密钥交给模型。

`state_engine.py` 是手机本地的确定性状态层：根据睡眠、步数和心率输出
`SLEEPING`、`AWAKE_IN_BED`、`STATIONARY`、`WALKING` 或 `EXERCISING` 及置信度，
并可生成 `possible_oversleep` 事件。它不能直接识别“躺着/坐着”，只报告带证据的
概率推断。`POST /v1/state/evaluate` 可在不依赖 Grok 的情况下运行这些规则；Grok
收到结构化事件后负责措辞和选项生成。

外部项目的职责划分见 [`docs/RESEARCH-TRIAGE.md`](../../docs/RESEARCH-TRIAGE.md)：
`miband-mcp` 适合作为 Agent/SQLite 同步层参考，BEST1503 SDK 适合作为固件刷写
研究底座，Gadgetbridge 仍是 Android 蓝牙和 Xiaomi protobuf 的底座。

固件研究产物：
[`n67cn-v3.1.190-resource-experiment.bin`](n67cn-v3.1.190-resource-experiment.bin)
是 50,330,500 字节的完整包，仅修改一个 MiSans 字体资源，SHA-256 为
`6941be39567efba5f7a123f58ea21b9e2b35ad95b30bf0870df2d0246663a63b`。它已通过
离线归档、CRC 和外层容器检查，但尚未在真实手环上验证 OTA 签名或刷写接受，
不能当作已解锁固件。

AstroBox 发送前的 MiWear mass envelope 可用
`tools/build_mass_firmware.py` 生成并校验；该 envelope 只负责 MD5/长度/CRC32
和分片传输，不能替代手环端签名校验。

`tools/build_ota_request_manifest.py` 会为同一文件生成 `PrepareOta` 请求清单，
其中版本为 `3.1.190`、MD5 与文件绑定，便于在 Android/Gadgetbridge 日志中核对
实际发送对象。

另有与当前设备版本匹配的 3.1.175 资源候选：
[`n67cn-v3.1.175-resource-experiment.bin`](n67cn-v3.1.175-resource-experiment.bin)。
它适合做结构对照；由于设备已经运行 3.1.175，实际 OTA 测试优先使用官方
3.1.190 升级路径对应的候选，避免同版本升级被设备策略拒绝。

另外生成了更小的增量候选：
[`n67cn-v3.1.190-font-incremental.bin`](n67cn-v3.1.190-font-incremental.bin)，
大小 590,301 字节，沿用官方 mode-2 外层组件，只携带 `version.ini` 和字体分区。
它通过归档/CRC 校验和 3.1.175→3.1.190 版本预检；设备签名验证与真机恢复能力仍未验证。

AstroBox 的主机端识别器会拒绝小于 1 MB 的固件文件，因此另有保留官方
9 个增量分区、再追加字体分区的版本：
[`n67cn-v3.1.190-font-incremental-fullset.bin`](n67cn-v3.1.190-font-incremental-fullset.bin)。
它大小为 8,270,038 字节，适合走 AstroBox/Gadgetbridge 的固件传输入口；官方分区
字节未改动，设备端签名接受仍未验证。

## 先确认型号与连接方式

核对源码：Gadgetbridge GitHub 镜像提交 a0948ee1cbc2a870f91d313f8e37df5f524465f7；
FreeBand 提交 3de0e60ebf754be13ecba4fe52f6a18e21c18a07。
Codeberg 本次访问被拒绝，因此镜像只作为可复现研究基线，不能当作最新上游。
正式开发须在可访问 Codeberg 后重新核对目标分支。

Band 9 Pro 的 MiBand9ProCoordinator 返回 BT_CLASSIC、isExperimental=true。
官方页面也标明实验性/支持程度未知。因此推荐 Android + Gadgetbridge fork；
不要直接用 bleak 实现整个客户端。具体固件是否另提供 BLE V2 仍需实测。
Gadgetbridge 是完整应用，不是可随意引用的 Maven 蓝牙 SDK。

## MVP 实施顺序

1. 记录手环地区、硬件/固件版本、官方 App 版本。已有配对保持不变。
2. Android 本地日志路径：/sdcard/Android/data/com.xiaomi.wearable/files/log/。
   可尝试 adb pull 导出到私有目录；检查 XiaomiFit.main.log、XiaomiFit.device.log
   或 Transfer.device.log 中 encryptKey/authKey/token/huamiAuthKey 对应的设备记录。
   只有精确 32 个十六进制字符才是 16 字节候选；用设备地址和认证结果验证。
   日志名、访问权限、是否输出密钥取决于版本。没有日志密钥不代表可以无 root
   读取私有数据库。已 root 自有设备可检查 device_db 的 device.detail，字段按版本核对。
3. iOS 路径参考 FreeBand KeyStore.swift：Mi Fitness 文件夹下
   VirtualDevice_registerList/manifest.sqlite，registerList* 行的 inline_data
   或 data/filename；其中的归档需要解码后读取 encryptKey。不能简单 grep 二进制。
4. 把 key 输入 Gadgetbridge 设备认证设置；官方 App 停止运行/撤销蓝牙权限，
   不在官方 App 解绑、不恢复出厂。首次绑定通常仍需官方 App/服务取得初始 key；
   本方案保证的是持有 key 后的日常本地同步，不保证全新设备离线首次激活。
5. 正常连接失败时，按 Gadgetbridge Xiaomi protobuf 文档在系统蓝牙先配对，
   手动添加准确型号和 MAC，尝试强制 Bluetooth Classic。不要随意改成 Band 10。
6. 第一次同步前启用 keep_activity_data_on_device。保持传输层 ACK，跳过的是
   XiaomiHealthService.ackRecordedData() 的应用层文件已同步确认。
7. 拉 today + past 文件列表。使用重叠 48–72 小时窗口覆盖跨午夜睡眠与更新版本，
   以设备 ID + file ID + SHA256 区分修订，原始文件永久归档由手机负责。
8. 首先验证一晚睡眠，再逐步接入 DailyDetailsParser 的心率/步数/血氧，
   DailySummaryParser 和 ManualSamplesParser。缺失值保留 null，不补成零。
9. 发中文短通知，分别验证开屏、锁屏、勿扰/睡眠模式和断连重试。

## 数据流与 Android 接入点

手环 → Gadgetbridge 连接/认证/下载 → 私有原始文件库 + 本地样本 DB
→ 持久化上传 outbox → HTTPS API → Grok bot → 通知 outbox
→ 手机拉取 → Gadgetbridge NotificationSpec → 手环。

使用原有 XiaomiSupport / XiaomiSppSupport / XiaomiAuthService / xiaomi.proto。
勿另开蓝牙连接。Java 适配源需放进 fork 对应 package；通过设备服务的现有
XiaomiSupport 生命周期接入，只有 INITIALIZED 状态才能调用。适配文件未做 Android 编译。

在 XiaomiActivityFileFetcher.addChunk() CRC32 通过后归档原始 bytes，保留 CRC；
调用现有解析器成功且 DB 事务完成后再创建上传任务。网络 I/O 不在蓝牙回调线程执行。
生产版建议复用 Gadgetbridge 已解析的 DB 样本；Python 解析器用于导出文件交叉检查。
此原型仅支持 sleep-stages v2，不声称覆盖所有 9 Pro 睡眠格式。

若保持 Gadgetbridge 无网络权限设计：使用独立 Android companion 上传，通过用户
授权的导出目录或新增 signature 保护的 IPC 读取数据。不能直接跨应用读取私有 DB。
若做个人 fork 内部上传：需显式添加 INTERNET 权限和网络 Worker，说明这是自定义构建。

本地 outbox 至少保存 event_id、device_id、payload、attempt、next_retry、state。
发送失败指数退避；不能把已提交本地队列当作手环已显示，更不能当作用户已阅读。
通知 ID 在手机持久化为稳定 int；手机重启后也要能去重。跨网络/蓝牙边界无法保证
严格 exactly-once，可能在崩溃恢复时重复，需要接受并限制重复提醒。

## 本地运行（Python 3.11+）

在本目录运行：

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m unittest -v
$env:PHONE_TOKEN = [guid]::NewGuid().ToString('N')
$env:AGENT_TOKEN = [guid]::NewGuid().ToString('N')
.\.venv\Scripts\python -m uvicorn api:app --host 127.0.0.1 --port 8000
```

浏览 http://127.0.0.1:8000/docs 查看完整交互 API。令牌每次重置后须重新配置客户端。
运行在远程服务器时配置 HTTPS 反向代理、请求体上限、访问控制和数据库备份。
此原型是单用户、单 Agent 轮询实现，不是多租户生产服务。

解析一份已经下载、重组且解密的完整原始文件：

```powershell
python sleep_file.py sleep.bin band-local-1 > sleep.json
```

所有 start/end 时间都是 UTC epoch 秒；timezone_offset_minutes 是文件记录的偏移。
不能额外给 epoch 时间再加八小时。阶段使用半开区间 [start,end)。
总时长使用设备提供的值，不强制等于各阶段相加；设备总时长与阶段边界可能不一致。
没有覆盖到的区间表示缺失，不填成清醒。unknown 阶段保留 raw_code。

## API 契约

| 请求 | 凭据 | 用途 |
|---|---|---|
| POST /v1/sleep | PHONE_TOKEN | 提交 sleep_file.py 输出；相同 event_id 幂等 |
| POST /v1/health | PHONE_TOKEN | 提交已解析的心率/步数/血氧样本；相同 event_id 幂等 |
| GET /v1/agent/pending | AGENT_TOKEN | bot 拉取未分析事件，最多 20 条 |
| GET /v1/agent/health/pending | AGENT_TOKEN | bot 拉取标准化健康样本 |
| POST /v1/agent/results/{event_id} | AGENT_TOKEN | 提交结构化分析/选项 |
| GET /v1/notifications | PHONE_TOKEN | 手机获取未提交且未过期通知 |
| POST /v1/notifications/{id}/submitted | PHONE_TOKEN | 标记已提交本地发送队列 |

认证头：Authorization: Bearer <对应令牌>。不接收或保存手环 auth key。
结果示例（expires_at 必须改为当前时间之后、24 小时以内）：

```json
{
  "title": "睡眠回顾",
  "text": "已生成本次回顾，请在手机选择下一步。",
  "options": [
    {"id":"view_details","text":"查看详情"},
    {"id":"set_reminder","text":"设置今晚提醒"}
  ],
  "expires_at": 1792674000
}
```

手机把 options 拼成编号文本显示；RPK 快应用则可以在支持的手环运行时显示并点击。
真正能否在你的 3.1.175 真机显示，仍需一次安装验收。
bot 在同一睡眠 start 的多个修订中选择更新内容，勿将同一晚重复统计；此 API 原型
保存全部事件，不自动合并修订。轮询不提供多 worker 租约，多 Agent 部署需补 lease。
模型调用的密钥、模型名和现有 bot 接入地址没有提供，本项目不虚构 Grok SDK 调用。
`agent_client.py` 会取得 pending、以 HMAC(timestamp + '.' + raw_body) 调用你的
Webhook，再按 Result schema 回写；`webhook_example.py` 可作为服务端校验模板。
失败事件保留在 pending 队列中，下一次调度自动重试，event_id 保持幂等。

单次运行 Agent 轮询器：

```powershell
$env:BAND_LOCAL_API = 'http://127.0.0.1:8000'
$env:AGENT_TOKEN = '至少 24 个字符的随机值'
$env:BAND_WEBHOOK_URL = 'https://你的域名/analyse'
$env:BAND_WEBHOOK_SECRET = '另一个至少 24 个字符的随机值'
python run_agent.py
```

手机侧通知桥接器负责把 Agent 结果交给 Gadgetbridge。它只调用 Android
`ACTION_SEND_APP_MESSAGE` 广播；Gadgetbridge 仍是唯一的蓝牙连接拥有者：

```powershell
$env:PHONE_TOKEN = '至少 24 个字符的随机值'
python phone_bridge.py --serial 192.168.10.189:37517 --once
```

手动发送一条 RPK 测试消息：

```powershell
python ..\..\tools\send_band_question.py --serial 192.168.10.189:37517 `
  --text '是否收到测试消息？' --option '收到' --option '重试'
```

确认测试成功后去掉 `--once`，它会按间隔轮询并在广播成功后标记通知已提交。
广播桥需要使用带 Xiaomi RPK/interconnect 支持的 Gadgetbridge 构建；普通上游
构建会安全失败并保留通知，便于稍后重试。

## 能力边界

- 可规划通知文字 + 按手环自身设置震动；无法保证越过勿扰、睡眠模式和系统限流。
- onFindDevice(true/false) 是诊断震动，可能打开查找界面，不能等价为自定义震动模式。
- 当前通知路径包含打开手机、清除和来电短信回复相关机制；来电 canned replies
  不能直接当作任意通知的选项按钮。需验证该固件是否支持通用 action/reply 回传。
- 真正手环选项优先研究可安装应用/RPK 与手机通信通道，逐型号验证运行时与安装能力。
  固件刷写、签名绕过或深度固件修改风险高，不属于 MVP。
- 可获取的是设备记录/计算后的指标与睡眠阶段，不能据此承诺原始 PPG/加速度波形。
- 不发送文件确认不等于无限留存，环形存储仍可能覆盖；每天归档，未解绑也需备份 key。

## 核对来源

- https://gadgetbridge.org/gadgets/wearables/xiaomi/#mi-band-9-pro
- https://gadgetbridge.org/basics/topics/xiaomi-protobuf/
- https://gadgetbridge.org/basics/pairing/huami-xiaomi-server/
- https://github.com/Freeyourgadget/Gadgetbridge/tree/a0948ee1cbc2a870f91d313f8e37df5f524465f7/app/src/main/java/nodomain/freeyourgadget/gadgetbridge/service/devices/xiaomi
- https://github.com/cobanov/freeband/tree/3de0e60ebf754be13ecba4fe52f6a18e21c18a07/ios/Freeband/Band

Gadgetbridge 源码文件带 AGPL-3.0-or-later 许可；FreeBand 带 MIT 许可。
复用时保留各自版权和许可，Android fork 按上游许可分发。
