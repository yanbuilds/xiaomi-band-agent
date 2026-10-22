# BEST1503 UART flasher evidence

The current [ATC1441 BEST1503 project](https://github.com/atc1441/MiBand10-BES2700iMP-BEST1503-Hacking)
was inspected at commit `f3dd7bd036011dada9f140c8dbc698f1499e71ac`.

## What it proves

- The BES2700iMP/BEST1503 family has a UART boot-ROM/SecondStage protocol with
  read and erase/write messages.
- The repository includes a host flasher and a `programmer.bin` blob, and its
  documented test board uses a 3.3 V USB-UART adapter at 921600 baud.
- The flasher's tested target is the Mi Band 10; the README says the same work
  is expected to apply to Band 9, but explicitly says the development and flash
  validation were done on Band 10.
- Its constants assume a 4 MiB flash at `0x28000000`. Our n67cn Pro evidence
  identifies a GD5F2GM7REYIG 256 MiB SPI-NAND and has no confirmed UART pad map.

## Consequence for n67cn Pro

This is a real, high-value reverse-engineering lead, not proof that the Pro can
be flashed with the same image or wiring. The next safe experiment would first
identify the Pro board revision and test pads, then use the flasher in read-only
mode to capture ROM/flash identity and a small memory window. No write command,
SecondStage upload, or power-cycle experiment should be attempted until that
mapping is confirmed and the stock flash is backed up.

The repository's custom firmware build also targets a different display geometry
and board configuration. It cannot be used as an n67cn image without adapting
the memory map, external flash driver, panel/touch drivers, boot header, and
recovery plan.
