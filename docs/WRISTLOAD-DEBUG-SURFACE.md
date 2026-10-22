# n67cn debug/factory surface (static only)

The pinned Wristload-Next source contains a small set of Vela debug messages
recovered from the official Xiaomi Fitness debug page. The relevant static
identifiers are:

| Command/subcommand | Observed purpose | Risk |
|---|---|---|
| `13/0` | Select boot mode; enum values include `user`, `userdebug`, `eng`, and `medical_meter` | Immediate restart; mode change may alter boot and service policy |
| `13/2` | Request a factory-test device-log dump | May expose identifiers and diagnostic data |
| `13/7` | Enter/start self-check mode | Changes device state; not needed for normal sync |
| `2/80` | Start device-log transfer | Transfers raw device logs to the host |
| `2/81` | Device-log completion/result notification | Read-only result event |

The source comments state that `13/0` restarts the device immediately. No
evidence shows that retail `n67cn` accepts the command, that it grants an
authenticated bootloader shell, or that it disables RSA verification. It must
therefore remain a static reverse-engineering lead, not an experimental
command to send.

The safe next use is to locate these command handlers in an authorized debug
APK or a passive SPP capture, then compare the returned status without changing
boot mode. A complete backup and recovery path is required before any stateful
factory command is considered.
