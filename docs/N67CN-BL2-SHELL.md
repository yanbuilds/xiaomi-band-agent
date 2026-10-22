# n67cn BL2 shell surface

The extracted `vela_bl2.bin` from the official n67cn 3.1.190 image contains
the NuttX 10.3.0 shell banner (`NuttShell (NSH 10.3.0)`) and the prompt
`bl2>`.  The image also contains `/dev/console`, `/dev/ttyS0`, `/dev/ttyS1`,
`/dev/bes_flash`,
`flash_bl`, `flash_bl2`, `flash_config`, `flash_ap`, `bes_reserved`, `dd`,
`reboot`, `resetcause`, `boardctl`, and the boot-mode values `bootloader`,
`recovery`, and `factory`.

This changes the hardware investigation: the next physical experiment should
look for the BL2 console on a confirmed UART or USB test interface, using a
current-limited, read-only probe.  The two tty names are candidates only; the
image does not map them to physical pads.  The normal magnetic charging cable
is not evidence of such an interface.  No pinout for the Band 9 Pro is
established by this file.

The BL2 banner also prints `SecureBoot Status` and the OTA path contains
`sign verify start`, `sign verify ok`, and `sign verify failed!`.  Therefore a
shell or raw flash writer, if reachable, must still be treated as a separate
question from accepting a modified OTA image.  The observed n67cn outer
RSA-2048/SHA-256 trailer remains the package acceptance gate; this report does
not claim a bypass.

Use the read-only inventory command:

```text
python tools/inventory_n67cn_bl2_shell.py work/firmware-lab/carved190/vela_bl2.bin --json docs/n67cn_bl2_shell_surface.json
```

The generated JSON records offsets so later disassembly or a UART capture can
be correlated without modifying the firmware.
