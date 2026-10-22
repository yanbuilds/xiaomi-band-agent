# Android ↔ Band Agent protocol

手机是唯一的 Bluetooth owner，也是唯一访问 Grok bot 的网络客户端。手环快应用只接收和发送小型 JSON 消息。

## 手机发给手环

```json
{
  "type": "question",
  "request_id": "sleep-20261022-01",
  "title": "睡眠回顾",
  "text": "今晚要不要提前半小时提醒休息？",
  "options": [
    {"id": "yes", "text": "好的"},
    {"id": "later", "text": "换个时间"},
    {"id": "no", "text": "今天不用"}
  ],
  "expires_at": 1792674000
}
```

## 手环回给手机

```json
{
  "type": "option_selected",
  "request_id": "sleep-20261022-01",
  "option_id": "yes"
}
```

手机必须校验：`request_id` 是否存在、是否属于当前设备、是否过期，以及选项是否确实存在。处理成功后回复：

```json
{"type":"ack","request_id":"sleep-20261022-01","text":"已提交"}
```

## 可靠性规则

- `request_id` 在手机端持久化，重复点击必须幂等。
- 手环显示“正在提交”不代表 Grok 已执行；只有收到 `ack` 才显示“已提交”。
- 断线时保留未发送消息，恢复连接后按过期时间丢弃。
- 选项最多 3 个，文字短于 60 个字符；详细分析只在 Android 展示。
- 语音回复暂不写进协议，待确认 3.1.175 是否能把麦克风数据或小爱识别文本交给第三方应用。

## Xiaomi interconnect binding

The Xiaomi protobuf `MessageContent` carries the app package name and its
fingerprint in addition to the JSON payload. The Android bridge must obtain
both values from the installed quick-app list before sending. Do not invent a
fingerprint and do not send to a package that is not currently installed.

The transport sequence is:

```text
list installed quick apps
  → find dev.xiaomi.bandagent
  → retain package_name + fingerprint
  → send MessageContent(JSON UTF-8)
  → receive MessageContent from the band
```

AstroBox's public Xiaomi core uses this exact `BasicInfo` pair for
`SendPhoneMessage`, `LaunchApp`, and status synchronization.

## Exact Xiaomi RPK subtypes

The CN Band 9 Pro implementation used by the open-source Gadgetbridge fork
`Sany18/Gadgetbridge` routes these messages inside `Command.type = 20`:

| subtype | direction | protobuf payload |
|---:|---|---|
| 6 | watch → phone | `RpkInfoList(id=packageName, sha=fingerprint)` status request |
| 7 | phone → watch | `RpkAppStatus(basicInfo, status=1)` |
| 8 | phone → watch | `RpkAppMessage(basicInfo, message)` |
| 9 | watch → phone | `RpkAppMessage(basicInfo, message)` |

`RpkInterconnectRouter.kt` contains a transport-neutral implementation of this
state machine. In production, map its `Command` values to the generated
`XiaomiProto.Command` builder in Gadgetbridge's `XiaomiRpkService`; do not
create a second Bluetooth connection or send a guessed fingerprint.
