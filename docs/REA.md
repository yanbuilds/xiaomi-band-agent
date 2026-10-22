# REA integration

[REA](https://github.com/morluto/rea) is useful as an analysis orchestrator,
not as a flashing authority. Its firmware workflow can hand regions to
Binwalk/Unblob and then to Ghidra, while its Android workflow can inspect the
Mi Fitness APK and capture authorized device behavior.

The local project already has a deterministic fallback for the Band 9 Pro
container:

```powershell
python tools/firmware_inspect.py work/firmware-lab/n67cn_v3.1.190_full.bin
python tools/list_embedded_archives.py work/firmware-lab/n67cn_v3.1.190_full.bin
```

When REA is available, the first useful command is:

```text
rea inspect-firmware-regions /absolute/path/to/n67cn_v3.1.190_full.bin
```

The expected investigation order is:

1. identify the outer header and all embedded resource regions;
2. extract the Vela/NuttX AP or resource payload, if present;
3. compare the 3.1.175 and 3.1.190 regions;
4. locate RPK loading, `system.interconnect`, notification, and vibrator code;
5. compare the findings with AstroBox and Gadgetbridge before designing a
   modification.

REA does not bypass Xiaomi signatures or make a modified image flashable. A
   successful static extraction is evidence for analysis only. Flash testing
   must use an unmodified, model-matched package first and retain a recovery
   path.
