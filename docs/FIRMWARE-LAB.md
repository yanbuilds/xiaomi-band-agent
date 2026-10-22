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
images and almost every byte differs between 3.1.175 and 3.1.190. The first
embedded ZIP header appears at offset `0x446f0`, and repeated ZIP-like resource
blocks follow it. The images are therefore packed resource containers rather
than flat MCU binaries; ordinary string replacement is not a viable
modification method. `tools/list_embedded_archives.py` enumerates these blocks.
The next target is the container/updater parser in AstroBox, rather than blind
binary patching.

The REA workflow and commands are documented in [REA.md](./REA.md). The
project keeps the local Python inspectors because they produce reproducible
reports even when external reverse-engineering providers are unavailable.

## New findings from AstroBox and the 9 Pro image

AstroBox's public Xiaomi core recognizes this format by the `\x60ZZ~` factory
header, a 32-byte version/`CONBINE_` descriptor, the `vela_ap.bin` marker, and
multiple ZIP local headers. The 9 Pro images satisfy those checks.

The 3.1.190 image also contains update-path strings for:

```text
/dev/flash_ap
/dev/flash_bl2
vela_ap.bin
vela_bl2.bin
verify start...
verify ok!
sign verify error(%d)
ota_upgrade_target
```

The image also embeds certificate/crypto string tables including RSA, EC
public keys, SHA-256/SHA-512, RSASSA-PSS, and the X.509 code-signing usage OID.
These strings alone do not reveal the vendor private key, but they strongly
support the conclusion that the updater verifies a signed package rather than
only checking a filename or CRC.

Both full images and the 3.1.175→3.1.190 incremental image contain the
`ENDSLEY/BSDIFF50` implementation strings. The incremental package therefore
contains a BSDIFF-style patch path in addition to the outer vendor container;
it is not a plain byte-for-byte replacement image. The full images also contain
`RPK` markers in their resource data, which is useful for locating quick-app
related metadata but is not evidence that the AP itself can load unsigned code.

This establishes that the normal update path can write both the AP and the
second-stage bootloader, and that CRC/signature checks happen before or during
that path. A modified AP or bootloader is therefore not a safe first target.
The project will prioritize signed RPK/resource installation and the existing
third-party app/interconnect messages, then use firmware research to understand
the verifier rather than attempting to bypass it.

Use `tools/firmware_container.py` for the authoritative outer-container view.
It uses the ZIP central directory instead of the first `PK` byte sequence,
because the raw vendor payload itself contains compressed bytes that look like
ZIP headers:

```powershell
python tools/firmware_container.py work/firmware-lab/n67cn_v3.1.190_full.bin \
  --extract-payload work/firmware-lab/n67cn_v3.1.190.payload
```

`tools/firmware_roundtrip.py` provides the packaging baseline. It currently
only performs a byte-identical copy and refuses any mismatch; this prevents a
resource patch experiment from being mistaken for a valid flashable package.

## Flashing gate

Before any write operation we need a verified device backup, the exact model
(`n67cn`), battery above 60%, a stable Bluetooth connection, and a known
recovery path. A modified image must also pass the device's package/signature
checks. Until those conditions are established, use the RPK quick-app route
for custom UI, interconnect messages, and vibration.
