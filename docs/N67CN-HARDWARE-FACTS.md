# n67cn Pro hardware facts relevant to flashing

The public teardown identifies the CN Smart Band 9 Pro model as `M2401B1`,
uses the BES2700iMP wearable SoC, and includes a GigaDevice `GD5F2GM7REYIG`
2-Gbit SPI NAND.  The teardown also reports the 1.74-inch 336-PPI display and
the other board devices.  Source: [52audio teardown](https://www.52audio.com/archives/218324.html).

The extracted n67cn `vela_ap.bin` independently confirms the NAND path.  Its
factory-test strings include:

```text
NANDFLASH_INFO=OK,device_id:0xC882C8,model:gd5f2gm7
bes_nand%d
nandflash_read_page
nandflash_write_page
nandflash_erase_block
nandflash_get_size
```

This changes the flasher assessment substantially:

- The ATC1441 ordinary-Band-9 flasher is documented for a 4-MB internal Flash
  window (`0x28000000` .. `0x283fffff`).
- n67cn Pro stores firmware/resources through a separate SPI-NAND driver and
  has a 2-Gbit storage device.
- Therefore the ordinary Band 9 4-MB Flash read/write command cannot be used as
  a Pro flasher without first recovering the BES NAND controller protocol,
  bootloader address map, bad-block handling, and the Pro board's UART pads.

The current candidate OTA package remains the correct low-risk format
experiment.  A true raw custom image needs a Pro NAND dump and a NAND-aware
recovery writer; we must not reinterpret the 50-MB OTA file as a 4-MB raw
image.
