# Band 9 Pro firmware lab

The device identifier for the China Xiaomi Smart Band 9 Pro is
`miwear.watch.n67cn`. The archive contains a precise incremental package for
the device version used in this project:

```text
miwear.watch.n67cn_v3.1.190_from_v3.1.175_incremental_360cb9c4.bin
size:   8,255,867 bytes
sha256: 360cb9c46b3df3170d44fab8216996d2f53d7c14226d254027a485cf6aecbc7f
```

The matching full images are also available for offline comparison:

```text
3.1.175 full: 50,302,103 bytes
sha256:       a8274e4cb29c427e020d08b7be109478750fb883498fd4bab0aad2064ef7131c

3.1.190 full: 50,330,500 bytes
sha256:       77174e6a39987ba6820796c3a20987c02fd3853fda0b85560bd5bddfad22deb4
```

The package header contains both `T1175` and `T1190` markers. That makes it a
candidate for a normal 3.1.175 → 3.1.190 update, but it does **not** prove that
third-party flashing is safe or that the image can be modified.

## Safe analysis workflow

1. Keep the original package and record its SHA-256.
2. Inspect headers, version markers, compression, and printable strings.
3. Compare the 3.1.175 and 3.1.190 full images only after obtaining both.
4. Look for Vela/NuttX, RPK loader, `interconnect`, notification, vibrator, and
   audio capability references.
5. Test an unmodified image with the supported updater before considering any
   modified image.

`tools/firmware_inspect.py` performs steps 1–2 only. It never patches or sends
   a firmware image to a device. Firmware files are intentionally kept out of
   Git because they are vendor copyrighted and large.

Initial measurements show approximately 8.0 bits/byte entropy in both full
images and almost every byte differs between 3.1.175 and 3.1.190. This is
consistent with a packed or encrypted container; ordinary string replacement
is not a viable modification method. The next useful target is the container
header and the updater/parser in AstroBox, rather than blind binary patching.

## Flashing gate

Before any write operation we need a verified device backup, the exact model
(`n67cn`), battery above 60%, a stable Bluetooth connection, and a known
recovery path. A modified image must also pass the device's package/signature
checks. Until those conditions are established, use the RPK quick-app route
for custom UI, interconnect messages, and vibration.
