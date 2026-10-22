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
5. Verify HMAC-SHA256(device key, `device_random || app_random || binding extra`).
   In the Wi-Fi call site this optional extra is the device's OOB/binding value;
   it is empty for the no-extra form.
6. Sign `app_random || device_random` with the app key.
7. Encrypt the device-info protobuf with AES-CCM using app key and nonce
   `app_iv || uint32_le(0) || uint32_le(0)`, with a 4-byte authentication tag.
8. Send command type `1`, subtype `27`, then wait for the device capability and
   confirmation response.

Gadgetbridge's checked-in `xiaomi.proto` matches the envelope used here:
`Command.type=1`, `Command.subtype=26/27`, `Auth.phoneNonce` field 30,
`Auth.watchNonce` field 31, and `Auth.authStep3` field 32. Its `AuthDeviceInfo`
also preserves the required proto2 defaults (`unknown1=0`, `unknown3=224`),
which is why the existing `XiaomiAuthService` can be reused for SPP.

`tools/xiaomi_wear_auth_v2.py` contains the reusable byte-level derivation,
signature, verification, and AES-CCM helpers. It deliberately does not read,
persist, or print an auth key. The remaining work for an independent client is
the proprietary protobuf envelope and the SPP command dispatcher, which are
already represented by Gadgetbridge's Xiaomi protobuf and SPP V2 classes.

The APK's `SppConnection` confirms that the 16-byte device secret is supplied
as `DeviceInfo.token` (converted to bytes) together with `userId` and
`appDeviceId`. This token is held in Mi Fitness private storage or obtained
from its authenticated binding service; it is not present in the public
shared-storage logs. That is why a non-root ADB extraction cannot safely
recover it.

This extraction explains why the direct BLE probe's earlier status-4 response
was inconclusive: the official app first uses a bound-device identifier and
application verification exchange, while the probe only exercised the generic
session layer.
