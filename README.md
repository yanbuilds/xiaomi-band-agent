# Xiaomi Band Agent

针对国行 Xiaomi Smart Band 9 Pro（HyperOS 3.1.175）的本地数据同步与 Agent 交互项目。

目标闭环：

```text
手环记录 → Android/Gadgetbridge → 私有 API → Grok bot
Grok bot → 选项/文本 → Android → 手环快应用/通知
```

本项目先实现健康数据和按钮交互，再研究语音接管。它不上传手环 auth key，也不把厂商固件直接提交到仓库。

## 当前内容

- `outputs/band9pro-mvp/`：睡眠 stages v2 离线解析器、FastAPI API、测试和 Gadgetbridge 适配骨架。
- `docs/ROADMAP.md`：产品与技术里程碑。
- `docs/VOICE-RESEARCH.md`：3.1.175 语音链路研究计划。

## 本地验证

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r outputs/band9pro-mvp/requirements.txt
$env:PYTHONPATH = (Resolve-Path outputs/band9pro-mvp).Path
.\.venv\Scripts\python -m unittest discover -s outputs/band9pro-mvp -v
```

Android 集成仍需放入 Gadgetbridge fork 编译；Python 原型不负责直接连接手环。

## 许可与研究材料

Gadgetbridge 代码按 AGPL-3.0-or-later 处理，FreeBand 按 MIT 处理。仓库只保存我们的代码、协议说明和脱敏测试向量；个人 auth key、厂商账号数据和未授权厂商固件不进入 Git。
docs/REVERSE-STATUS.md records the validated firmware component extraction and signing barrier.
