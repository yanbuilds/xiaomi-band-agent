# n67cn AP AT-command surface

The extracted 3.1.190 AP contains a compiled list of `AT^...` command names.
It includes factory and diagnostic operations such as `AT^DID?`, `AT^KEY?`,
`AT^LOGZIP`, `AT^INTERCONNECT`, and `AT^OTA_UPDATE`; it also contains names
that could change boot or storage state, including `AT^JUMP`, `AT^FTYRESET`,
`AT^REBOOT`, `AT^NEW_FILE`, and `AT^CLEAN_DIR`.

The same AP symbol index places notification and haptic functions in the same
image, including `notifications_mass_data_page_handle`, `parsing_protobuf`,
`vibrator_set_mode`, `vibrate_driver_start`, and `vibrate_driver_stop`. This
confirms that notification and vibration behavior is implemented in the AP
image; it does not expose a new host command or make those functions safe to
call directly.

This is useful evidence for locating the factory command dispatcher during
future disassembly. It is not an unlocked interface: a string table does not
show which transport reaches the parser, whether a session is authenticated,
or whether the command is compiled out in the retail build. No command has
been sent to the band.

Run the static audit with:

```text
python tools/inventory_n67cn_at_surface.py \
  work/firmware-lab/vela_ap.bin \
  --json docs/n67cn_at_surface.json
```

The report is deliberately read-only. Any later hardware work must start with
a passive UART/USB capture and a complete flash backup. In particular, the
high-risk names must not be used as a substitute for a verified recovery path,
and they do not bypass the n67cn RSA signature check.
