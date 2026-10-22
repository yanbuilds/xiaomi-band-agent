# n67cn BLE V2 evidence

This is a redacted field report for Xiaomi Smart Band 9 Pro CN, firmware
3.1.175. No address, serial number, auth key, Xiaomi account identifier, or
captured health payload is stored here.

## Observed

- Windows BLE scan finds the band and a direct connection succeeds.
- Service `0000fe95-0000-1000-8000-00805f9b34fb` is present.
- `0000005e-0000-1000-8000-00805f9b34fb` is notify/RX.
- `0000005f-0000-1000-8000-00805f9b34fb` is write-without-response/TX.
- The A5 A5 frame layer accepts `START_SESSION_REQUEST` and returns a session
  configuration frame. This confirms that a direct BLE client can reach the
  Xiaomi protobuf transport without Classic Bluetooth pairing.
- The first protobuf authentication request is acknowledged. With the current
  local Mi Health credential set the firmware returns an auth status 4 instead
  of a watch nonce. The client therefore stops before HKDF, encryption, data
  reads, notifications, or vibration.

## Safety

The probe only sends session setup, authentication, and protocol ACK frames. It
does not send activity-file confirmations, firmware-install commands, RPK
install commands, or flash commands. Credentials are read from an ignored
local file and are never logged.

## Next diagnostic

Status 4 must be resolved before testing encrypted commands. The likely causes
are a still-owned Mi Fitness binding or a model-specific BLE authentication
variant. We should first release the official-app connection/binding and retry,
then compare the exact auth protobuf with Xiaomi's Android implementation.

## 2026-10-23 credential-material retry

The latest shared Mi Fitness log contains 16-byte `encryptKey` and
`beaconKey` fields, while its `authKey` field is null. A fresh probe using the
latest local `encryptKey` again reached session setup but returned status 4
before a watch nonce. No encrypted command, vibration, health read, or file
confirmation was sent. This rules out treating the logged `encryptKey` as a
standalone replacement for the SPP binding token.
