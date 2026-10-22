# Gadgetbridge OTA path for n67cn

The Sany18 Gadgetbridge fork already has the correct Xiaomi upload pipeline:

1. `XiaomiSystemService.installFirmware()` sends a firmware-install protobuf
   with the selected version and the MD5 of the exact file bytes.
2. After status `0`, `XiaomiDataUploadService` sends type `0x20` (firmware).
3. The upload body is `0x00 | 0x20 | MD5 | length (little-endian) | bytes |
   CRC32 (little-endian)`, split into chunks after the four-byte part header.

The public `XiaomiFWHelper` currently recognizes only an older Band 8 Pro
header.  n67cn files begin with `` `ZZ~ `` and then an ASCII descriptor, so the
helper rejects them before the upload path starts.  Apply
[`android-bridge/patches/gadgetbridge-n67cn-firmware-header.patch`](../android-bridge/patches/gadgetbridge-n67cn-firmware-header.patch)
to the Gadgetbridge fork.  The patch accepts both full (`3.x.y`) and
incremental (`CONBINE_...`) n67cn descriptors while keeping the existing
upload service unchanged.

The patch changes only `parseAsFirmware()`.  A source diff audit confirms that
the MD5 calculation, `TYPE_FIRMWARE = 0x20`, size field, resume offset, chunk
header, and CRC32 code are untouched.  The local fork's `git apply --check` and
`git diff --check` both pass.  Full Gradle compilation still requires the
Gradle 9.5.1 distribution, which is not cached in this environment.

Use the generated OTA JSON manifest to log the same version and MD5 that are
sent in the protobuf request.  Test with an unmodified official image first;
the watch performs its own signature and package checks after transfer.
