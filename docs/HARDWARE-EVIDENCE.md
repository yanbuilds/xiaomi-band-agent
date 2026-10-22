# Band 9 Pro hardware evidence

Public teardown reports identify the China Band 9 Pro board as using the
BES2700iMP wearable SoC and GD5F2GM7REYIG 256 MB SPI-NAND/flash device. They
show the charging contacts and main PCB, but do not publish a UART pinout or a
bootloader unlock procedure.

- [EEF Focus teardown](https://www.eefocus.com/video/1779825.html)
- [52audio teardown](https://www.52audio.com/archives/218324.html)

This supports the firmware lab's BES2700/n67cn identification, but it is not
enough evidence to probe arbitrary pads. The current safe hardware gate remains
a board photograph with pad labels or an established community pinout, followed
by voltage-limited, read-only UART capture.

The dedicated BES2700 hacking repository still lists “UART pads on Mi Band 9
Pro” as an open issue, with no published pad map or working dump procedure:
[atc1441 issue #4](https://github.com/atc1441/MiBand10-BES2700iMP-BEST1503-Hacking/issues/4).
The issue remains open with no maintainer reply as checked on 2026-10-23, so it
does not provide a usable UART route for the current unit.
