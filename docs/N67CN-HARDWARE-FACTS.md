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

The same AP also contains YAFFS diagnostics (`yaffs: NAND geometry problems`,
ECC fixed/unfixed messages, block retirement, and `inband_tags`).  The raw
storage is therefore a managed YAFFS/NAND volume, rather than a flat file
stream.  A safe writer must preserve YAFFS tags and bad-block retirement rules;
blindly placing the 50-MB OTA bytes at NAND offset zero would destroy the
filesystem metadata.

For planning a future reader, the GD5F2GM7 datasheet specifies a nominal
2-Gbit device with 2,048-byte pages and internal-ECC page storage of 2,048 +
64 bytes.  The conservative model used by
`tools/n67cn_nand_geometry.py` is 64 pages per 128-KiB erase block and 2,048
nominal blocks.  These values are not yet a writer specification: the actual
device must be read first to confirm OOB layout, ECC mode, bad-block markers,
and any vendor-reserved blocks.  See the [official GigaDevice datasheet](https://download.gigadevice.com/Datasheet/DS-00820-GD5F2GM7UE-Rev1.5.pdf).

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

Once a read-only dump is available, run
`tools/analyze_gd5f2gm7_dump.py dump.bin --oob 64`.  It reports complete pages,
128-KiB erase blocks, and candidate bad-block markers without modifying the
device.  The marker result is deliberately labelled a candidate until it is
cross-checked against the n67cn `bes_nand_isbad` implementation.
