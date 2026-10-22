# Band 9 Pro firmware reverse-engineering status

## What is now verified

The `n67cn` 3.1.190 full image is a concatenation of validated ZIP blocks,
not one opaque blob.  The following components can be carved and CRC-checked
offline with `tools/carve_firmware_components.py`:

| Component | Offset in 3.1.190 | Compressed | Expanded | CRC32 |
|---|---:|---:|---:|---|
| `vela_bl.bin` | `0x0e2d65` | 43,981 | 63,712 | `79a63085` |
| `vela_bl2.bin` | `0x0ed9e2` | 191,390 | 299,516 | `b09a24a5` |
| `vela_ap.bin` | `0x14d448` | 4,817,085 | 7,775,288 | `539f3a43` |
| `vela_factory.bin` | `0x5e55b5` | 1,402,742 | 2,196,112 | `a895cb05` |

The AP image begins with a 14-byte vendor header.  Disassembling from
`0x0c10000e` as Thumb code produces valid ARM instructions, consistent with
the public Vela startup analysis.  The AP image contains the firmware's
notification, interconnect, sleep, heart-rate, and vibration symbol strings,
so the next stage can be done against the extracted image instead of the
compressed outer container.

The official `3.1.190_from_3.1.175` incremental package contains the same
`vela_bl.bin`, `vela_bl2.bin`, `vela_ap.bin`, and `vela_factory.bin` bytes as
the 3.1.190 full image; it is a smaller wrapper whose only unique payload is
the NFC resource.  This gives us a reliable reference for reconstructing the
container layout, but it also confirms that changing AP bytes would change a
signed component rather than merely changing a UI resource.

The AP also embeds the same 2048-bit RSA public modulus found in the outer
firmware at AP offset `0x5b99e7`.  Its SHA-256 fingerprint is
`f4ffe419c16bc3554f7e2172021e6493aa6c2fc05580cd4fd820eac4a7fcc8a9`.
This is strong evidence that AP/boot updates are verified with a vendor key.
No private signing key is present in the public archives.

The OTA-related code has explicit `app_verify` strings for reading a ZIP
central-directory offset and a `signature_block`, hashing the signed bytes,
then calling `mbedtls_pk_verify`/`verify_block_signature`.  That is a real
verification path, rather than a guessed CRC-only check.  The public key is
also present in the OTA code's read-only data.  This is why the resource-only
repack is useful as a format experiment but cannot yet be called an unlocked
firmware image.

## Reproducible extraction

The outer image is not a ZIP by itself.  Its 92-byte header gives the exact
end of the first `vela_ota.bin` component.  `extract_n67cn_outer.py` reads that
offset and writes the complete component, including its final trailer bytes:

```powershell
python tools/extract_n67cn_outer.py `
  work/firmware-lab/n67cn_v3.1.190_full.bin `
  --component work/firmware-lab/vela_ota_exact.bin `
  --manifest work/firmware-lab/vela_ota_exact.json
```

For 3.1.190 and 3.1.175 the component is 575,816 bytes and starts with the
same Vela image header.  The versions differ in their trailer digest/metadata;
therefore the component must be extracted from the matching full image rather
than copied between releases.  This is a read-only container operation and does
not alter the image or produce a flashable package.

```powershell
python tools/carve_firmware_components.py `
  work/firmware-lab/n67cn_v3.1.190_full.bin `
  --output work/firmware-lab/carved190 `
  --name vela_bl.bin --name vela_bl2.bin --name vela_ap.bin `
  --name vela_factory.bin --name notifications.res --name sleep.res
```

The tool deliberately validates the ZIP version, compression stream, expanded
size, and CRC32.  This rejects the many accidental `PK\x03\x04` byte sequences
inside ARM code.

As a controlled repack test, `tools/patch_resource_experiment.py` flips one
font byte while keeping the resource's expanded size, compressed size, ZIP
offsets, and CRC metadata consistent.  The resulting local candidate has
SHA-256 `6941be39567efba5f7a123f58ea21b9e2b35ad95b30bf0870df2d0246663a63b`.
The container parser and ZIP CRC check both pass.  This is a structural test
artifact only; it has not been sent to a band and is not claimed to pass the
device's OTA verifier.

## Concatenated archive map

The full n67cn image contains 258 independent ZIP archives after the outer
header, rather than one monolithic ZIP.  `index_n67cn_archives.py` reconstructs
each archive boundary from its EOCD and central-directory fields.  The first
3.1.190 archives are the touch/display firmware, boot blocks, AP, factory image,
and resource blocks; the last archives contain the MiSans font files.  The
archives are separated by four bytes and have stable offsets within a release.

```powershell
python tools/index_n67cn_archives.py `
  work/firmware-lab/n67cn_v3.1.190_full.bin `
  --json work/firmware-lab/n67cn_archives_190.json
```

`patch_n67cn_archive.py` can now produce a reproducible, size-preserving
resource experiment by changing one non-code ZIP member and updating its local
and central-directory CRCs.  Rebuilding the MiSans archive at `0x2ffc321`
produces the same candidate SHA-256 as the earlier experiment.  Re-indexing
shows 258 valid archives and exactly one changed archive, which proves that the
candidate is a correctly formed container.  It does not prove the vendor
signature policy will accept that resource change.

`validate_n67cn_package.py` additionally inflates every ZIP member, checks all
CRC values, and verifies that `version.ini` reports the actual archive count.
Both the official 3.1.190 image and the resource candidate pass these checks.

The same indexer finds a 9-archive 3.1.175→3.1.190 incremental package.  It
contains the official AP, BL2 and factory blocks plus language/NFC resources.
The patcher permits non-`.bin` members in this incremental form, while
requiring an explicit byte offset when a large compressed member would make a
blind equal-length search impractical.  No incremental resource candidate is
claimed until it passes the same full inflate/CRC checks.

The OTA component embeds the vendor RSA public key as a 512-character hex
modulus with exponent `10001`.  AP strings expose
`app_verify_info`, `central_directory_offset`, `signature_block`, and
`mbedtls_pk_verify`.  This confirms a signed application-block path exists, but
the public archives contain no private signing key.  The resource experiment
therefore remains the highest-confidence package-format test, not an unlocked
firmware image.

## Consequence for a flashable custom image

We can now edit and rebuild resources locally, and we can inspect AP/boot
control flow with Ghidra or Binary Ninja.  A modified AP or bootloader is not
yet a safe flashable image: the embedded public key means the corresponding
signature must be produced by Xiaomi's private key, or the device must expose
an unlocked recovery/bootloader path.  The next experiment is therefore a
read-only signature-path trace and a protocol-level notification proof of
concept.  Do not flash a locally modified image until the device accepts its
signature and the updater reports a verified result.
# Related BEST1503 research

`atc1441/MiBand10-BES2700iMP-BEST1503-Hacking` is directly relevant to the
hardware layer: its README identifies the Band 9/10 application processor as
BES2700iMP/BEST1503, reconstructs the display/touch HAL, and documents a UART
SecondStage flashing flow. The author states that the SDK was tested on Band
10 and is expected to apply to Band 9; that is useful evidence, not proof for
the China Band 9 Pro (`n67cn`) board, pinout, bootloader policy, or 3.1.175
image. It also replaces stock firmware, unlike our RPK route.

We therefore use it for chip-family and flasher research while keeping the
Band 9 Pro path staged: back up flash, identify the exact board test pads and
bootloader handshake, then validate a minimal recovery image on sacrificial
hardware before attempting any custom firmware. For the Grok interaction goal,
the signed Quick App/RPK path remains the lower-risk deliverable because it
already exercises the CN Band 9 Pro interconnect and vibration APIs.

# FreeBand protocol cross-check

The current `cobanov/freeband` source is useful for the phone-side protocol,
even though it targets Band 10/10 Pro on iOS. Its documented and tested path
matches the protocol artifacts in this repository: service `FE95`, notify
characteristic `005E`, write characteristic `005F`, 16-byte auth key, HKDF
SHA-256 with info `miwear-auth`, AES-CCM for the authentication introduction,
then AES-128-CTR protobuf frames with `A5 A5` framing and CRC16. It also has a
working notification command and activity-file list/fetch flow, and explicitly
avoids file acknowledgement while preserving raw files.

The implementation is not copied wholesale into Android: FreeBand's Swift
BLE lifecycle and Band 10 command map still require validation against the
China Band 9 Pro's Gadgetbridge transport. We use it as an independent
cross-check for crypto/frame vectors and as the reference for activity-file
parsing; the Android Bluetooth owner remains the Sany18/Gadgetbridge Xiaomi
service. Source: [FreeBand](https://github.com/cobanov/freeband).


# n67cn package experiment

The local `n67cn_v3.1.190_font-test2.bin` experiment is size-preserving and
keeps the 92-byte outer Vela header byte-identical. `validate_custom_firmware.py`
reports only three changed ranges: the compressed resource byte and the local
and central ZIP CRC32 fields. The candidate therefore passes offline structural
checks and can be supplied to an OTA client as a normal full-image file.

This is not yet a verified flashable custom firmware: the device-side verifier,
component policy, and recovery behavior have not been tested on a physical
`n67cn` unit. It is the correct artifact for the next controlled test because
it changes one non-code resource while leaving bootloader, AP, factory image,
outer metadata, and file length unchanged.
