# Phone-side extraction (redacted)

Date: 2026-10-23. Device: OPPO PGEM10, Xiaomi Fitness 3.59.1, paired product `miwear.watch.n67cn` (Band 9 Pro, CN).

## What was copied

The following public/shared-storage material was copied over ADB into the ignored `work/mihealth-extract/` directory for offline inspection:

- Mi Fitness device/transfer logs
- Mi Fitness sleep-advice JSON templates
- The installed `com.mi.health` APK, copied to `work/mihealth-apk/`

The working directory is ignored and no credentials, account tokens, MAC address, device ID, or key bytes are committed or printed.

## Findings

The logs establish the actual transport used by this Band 9 Pro session:

- Mi Fitness connects through Classic Bluetooth SPP, not the direct BLE V2 path used by the first probe.
- Transport version reported by the watch is `2.1.2`.
- The framing starts with `A5 A5`; the logs show command/data/ACK sequencing and a negotiated 32 KiB maximum packet size.
- Authentication is an application verification exchange: `sendAppVerify` followed by `sendAppConfirm`. The application reports `verify sign success` and the watch region as `CN` before data-sync calls begin.
- After confirmation, Mi Fitness issues capability and sync calls over protobuf transport.
- The app APK contains the classes and symbols `WearAuthV1`, `WearAuthV2`, `WearAuthWrapper`, `getAuthKey`, `getEncryptKey`, `getBeaconKey`, `readBeaconKeyFromDevice`, `sendAppVerify`, and `sendAppConfirm`.

This is useful protocol evidence, but it is not an extracted auth key. The APK is not debuggable (`run-as com.mi.health` is rejected), so Android's normal ADB shell cannot read `/data/user/0/com.mi.health` where account/device credentials are stored. The shared-storage logs also do not contain a usable key in plaintext.

## Safe next step

Use the SPP transport path as the primary implementation target and instrument only our own debug build or a user-authorized rooted test device if key extraction is still required. Do not attempt to brute-force, patch, or flash the bootloader. The direct BLE V2 probe remains a separate experiment and currently receives authentication status 4 from firmware 3.1.175.

For a user-authorized, shared-storage-only copy of the logs, use
`tools/pull_mifitness_logs_safe.ps1`. It defaults to a dry-run and writes only
to ignored `work/` when `-Pull` is supplied; it never reads `/data/user/0`,
prints credentials, or modifies the phone.
