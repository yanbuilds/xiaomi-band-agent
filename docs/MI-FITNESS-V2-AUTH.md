# Mi Fitness V2 authentication extraction

Static analysis of the locally copied Mi Fitness 3.59.1 APK reached the
`WearAuthV2` implementation. The relevant decompiled classes are kept only in
the ignored `work/mihealth-decompiled2/` directory; no APK or private data is
committed.

The observed sequence is:

1. Generate a 16-byte app random value.
2. Send command type `1`, subtype `26`, containing the app random value and the
   bound device identifier.
3. Receive a device random value and device signature.
4. Derive 64 bytes with HKDF-SHA256 using the secret key as input keying
   material, `app_random || device_random` as salt, and `miwear-auth` as info.
   The first 16 bytes are the device AES key, the next 16 the app AES key, and
   the following 4-byte pairs are device/app IV prefixes.
5. Verify HMAC-SHA256(device key, `device_random || app_random || device name`).
6. Sign `app_random || device_random` with the app key.
7. Encrypt the device-info protobuf with AES-CCM using app key and nonce
   `app_iv || uint32_le(0) || uint32_le(0)`, with a 4-byte authentication tag.
8. Send command type `1`, subtype `27`, then wait for the device capability and
   confirmation response.

`tools/xiaomi_wear_auth_v2.py` contains the reusable byte-level derivation,
signature, verification, and AES-CCM helpers. It deliberately does not read,
persist, or print an auth key. The remaining work for an independent client is
the proprietary protobuf envelope and the SPP command dispatcher, which are
already represented by Gadgetbridge's Xiaomi protobuf and SPP V2 classes.

This extraction explains why the direct BLE probe's earlier status-4 response
was inconclusive: the official app first uses a bound-device identifier and
application verification exchange, while the probe only exercised the generic
session layer.
