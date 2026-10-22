# Wristload-Next route for n67cn

The public [Wristload-Next](https://gitcode.com/pengchegnkai/Wristload-Next)
project is a useful independent cross-check of the Band 9 Pro transport. Its
README reports real-device confirmation of:

```text
RFCOMM -> L1START -> sendAppVerify -> sendAppConfirm -> device ready
```

It also implements watch-face Mass transfer and the RPK flow:

```text
(20,1) prepare -> Mass dataType 0x40 -> (20,2) result
```

The project stores auth keys in OS secure storage and requires the user to
provide a 32-character (16-byte) key. It does not scrape credentials or put
them in logs. Its protocol notes say the firmware OTA channel is currently
only identified, not sent, and that firmware installation remains disabled
pending protocol evidence.

## Relevance to this repository

- It independently confirms that the n67cn path is Classic Bluetooth RFCOMM,
  matching the Mi Fitness logs and the Gadgetbridge SPP patch here.
- Its `abu`/`bc0`/`hc0` authentication and L1START details are a second source
  for improving our local bridge.
- Its RPK path is a practical, device-tested control path for notification,
  vibration, and Grok interaction while the signed firmware path remains
  unresolved.
- It does **not** provide a bootloader unlock, a private Xiaomi signing key,
  or a verified custom firmware flashing procedure.

The third-party checkout is kept under ignored `work/` for read-only analysis;
no source, device identifier, auth key, or raw log is copied into this repo.
The locally reviewed snapshot is pinned at commit
`3ecfd2444d37e0f888c8ed42da86a56733acd55a` for reproducibility.
