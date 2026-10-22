# MiWearBridge route for n67cn testing

[MiWearBridge](https://github.com/batareya16/MiWearBridge) is a useful
additional test harness for the Android side.  It hooks Mi Fitness with
LSPosed and exposes the existing third-party app/watchface/firmware install
flow, plus the `@system.interconnect` online announcement and coordinator
routing needed by the Grok Quick App.

## What it changes for this project

- It can install the generated `.rpk` and route phone ↔ watch messages without
  Xiaomi partner onboarding.
- It can submit an OTA candidate through Mi Fitness's own firmware sender, so
  the device-side result can be compared with Gadgetbridge logs.
- It can pull Mi Fitness device logs and expose the stored EncryptKey, which
  may help correlate OTA failures with the n67cn verifier.

## Hard requirements

- rooted Android with LSPosed;
- Mi Fitness installed and the band connected;
- the phone companion and RPK must use the same signing key for interconnect;
- a complete official-package recovery path before sending a modified image.

The repository does not bypass the n67cn bootloader signature.  Its firmware
menu only improves the sender and logging path; the candidate still has to
pass the watch's own verification.  This is therefore a useful acceptance
harness, not a new firmware signing method.

## Recommended experiment order

1. Install an unmodified official 3.1.190 package and save Mi Fitness logs.
2. Install the debug RPK and verify interconnect/vibration first.
3. Send the resource-only candidate and capture the first verifier failure or
   rollback message.
4. Stop before any AP/bootloader candidate unless a full NAND/UART backup and
   recovery path exist.
