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

The AP also embeds the same 2048-bit RSA public modulus found in the outer
firmware at AP offset `0x5b99e7`.  Its SHA-256 fingerprint is
`f4ffe419c16bc3554f7e2172021e6493aa6c2fc05580cd4fd820eac4a7fcc8a9`.
This is strong evidence that AP/boot updates are verified with a vendor key.
No private signing key is present in the public archives.

## Reproducible extraction

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

## Consequence for a flashable custom image

We can now edit and rebuild resources locally, and we can inspect AP/boot
control flow with Ghidra or Binary Ninja.  A modified AP or bootloader is not
yet a safe flashable image: the embedded public key means the corresponding
signature must be produced by Xiaomi's private key, or the device must expose
an unlocked recovery/bootloader path.  The next experiment is therefore a
read-only signature-path trace and a protocol-level notification proof of
concept.  Do not flash a locally modified image until the device accepts its
signature and the updater reports a verified result.
