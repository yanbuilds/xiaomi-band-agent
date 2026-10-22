# Gadgetbridge SPP build

Built locally on 2026-10-23 from the `xiaomi-app-messaging` worktree after changing `MiBand9ProCoordinator` to `ConnectionType.BT_CLASSIC`.

- Gradle task: `:app:assembleMainlineDebug`
- Result: successful
- APK: `outputs/band9pro-mvp/gadgetbridge-spp-debug.apk`
- SHA-256: `2e75a7dba77514902e8a2a3db44236dd3ce855a13f0add6a430d3f6fcc59e0c`
- Size: 36,487,184 bytes

This is a debug APK for protocol testing. It is not a firmware image and cannot be flashed to the band. Installation and device pairing are intentionally left as a separate, user-visible step. The APK does not contain the Mi Fitness account credentials or the user's auth key; Gadgetbridge reads an auth key only from its own per-device preferences.

The coordinator change is recorded in `patches/gadgetbridge-n67cn-spp.patch`.
