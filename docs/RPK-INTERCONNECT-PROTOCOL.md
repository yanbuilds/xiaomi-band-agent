# n67cn RPK interconnect protocol

The independent `Sany18/smart-band` repository was checked at commit
`25c0401f2e16816643cedb3c6c9413122e8c3525`. Its protocol notes describe the
phone-to-RPK channel used by Band 9 Pro:

- RPK package integrity is a `META-INF/CERT` zip containing `hash.json`; it is
  not an AP/BL firmware signature.
- `@system.interconnect` uses Xiaomi protobuf command type `20`.
- The watch announces package name and a real 20-byte fingerprint (subtype 6).
- The phone must echo that exact fingerprint in the connected status (subtype 7)
  before sending messages (subtype 8); watch-to-phone messages are subtype 9.
- Watch-to-phone `conn.send({data:{data: "..."}})` is JSON-wrapped as
  `{"data":"..."}` on the wire. Phone-to-watch messages are sent as raw
  protobuf payloads.

The fingerprint must be stored only in the active device session. It is not a
credential and must not be logged with device identifiers. Our future
Gadgetbridge adapter should implement this as a bounded message queue, reject
unknown package names, and keep the existing single Bluetooth owner.

This channel is the current route for Grok responses, notification text,
choice IDs, and vibration requests. It does not change the signed AP/BL
firmware and therefore cannot be used as evidence that a custom firmware image
is flashable.

Reference: [Sany18/smart-band protocol notes](https://github.com/Sany18/smart-band/tree/main/protocol-notes).
