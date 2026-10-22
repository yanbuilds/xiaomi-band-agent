# Band 9 Pro auth-key routes

## Current evidence

The shared Mi Fitness logs contain `encryptKey` and `beaconKey`, but the
`authKey` field is null. The private `com.mi.health` storage cannot be read
with `run-as` because the release APK is not debuggable. No credential values
are stored in this repository.

## Candidate route from public research

The [Sany18/smart-band notes](https://github.com/Sany18/smart-band) describe a
no-root workflow for a China Band 9 Pro:

1. Pair and bind the band in Mi Fitness.
2. Force-stop Mi Fitness.
3. Use Notify for Mi Band to inspect the already-bonded device and read its
   pairing key.
4. Force-stop Notify before handing the key to Gadgetbridge.

This is a credential-recovery route, not a firmware-unlock route. It should be
performed only on the user's phone, with the key copied through a local
clipboard or QR transfer and never pasted into chat, logs, Git, or cloud
issue trackers. The key must be treated like a password and rotated by
unbinding/rebinding if it is exposed.

## Guardrails for implementation

- Do not install or launch a third-party companion while the phone is locked.
- Do not scrape private app data or bypass Android access controls.
- Keep the key in an ignored, access-controlled local file and redact all
  diagnostics.
- Test authentication before sending any historical-data or notification
  command; a failed handshake must not trigger retries in a loop.

Once a user-supplied key is available, the existing Gadgetbridge SPP build can
exercise the Band 9 Pro protocol without changing firmware. It still does not
provide a vendor signature or a custom flash path.
