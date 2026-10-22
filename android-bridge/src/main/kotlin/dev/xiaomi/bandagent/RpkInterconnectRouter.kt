package dev.xiaomi.bandagent

/**
 * Xiaomi RPK interconnect command routing, kept independent from Gadgetbridge.
 *
 * The Bluetooth owner (Gadgetbridge/AstroBox) is responsible for framing,
 * encryption and protobuf serialization. This class supplies the exact RPK
 * subtype decisions and remembers the fingerprint announced by the watch.
 * It can therefore be dropped behind either an existing Gadgetbridge service
 * or a generated XiaomiProto.Command adapter without rewriting the protocol.
 */
class RpkInterconnectRouter(
    private val packageName: String,
    private val send: (Command) -> Unit,
    private val onMessage: (ByteArray) -> Unit,
) {
    companion object {
        const val COMMAND_TYPE = 20
        const val STATUS_REQUEST = 6
        const val STATUS_RESPONSE = 7
        const val MESSAGE_TO_WATCH = 8
        const val MESSAGE_FROM_WATCH = 9
        const val CONNECTED = 1
        const val DISCONNECTED = 2
        const val MAX_MESSAGE_BYTES = 4096
    }

    /** The protobuf fields needed by this router. */
    sealed interface Command {
        val subtype: Int

        data class Status(
            val packageName: String,
            val fingerprint: ByteArray,
            val status: Int,
        ) : Command {
            override val subtype: Int = STATUS_RESPONSE
        }

        data class Message(
            val packageName: String,
            val fingerprint: ByteArray,
            val payload: ByteArray,
        ) : Command {
            override val subtype: Int = MESSAGE_TO_WATCH
        }
    }

    private var lastFingerprint: ByteArray? = null

    /** Handle subtype 6: echo the watch-provided fingerprint, never invent one. */
    fun onStatusRequest(requestedPackage: String, fingerprint: ByteArray) {
        require(requestedPackage == packageName) { "unexpected RPK package" }
        require(fingerprint.isNotEmpty()) { "watch did not provide a fingerprint" }
        lastFingerprint = fingerprint.copyOf()
        send(Command.Status(packageName, fingerprint.copyOf(), CONNECTED))
    }

    /** Handle subtype 9: pass UTF-8 JSON to the application layer. */
    fun onMessageFromWatch(requestedPackage: String, payload: ByteArray) {
        require(requestedPackage == packageName) { "unexpected RPK package" }
        require(payload.size <= MAX_MESSAGE_BYTES) { "interconnect payload too large" }
        onMessage(payload.copyOf())
    }

    /** Build subtype 8 using the fingerprint most recently announced by watch. */
    fun sendMessageToWatch(payload: ByteArray) {
        require(payload.size <= MAX_MESSAGE_BYTES) { "interconnect payload too large" }
        val fingerprint = lastFingerprint
            ?: error("RPK status request has not arrived; do not guess fingerprint")
        send(Command.Message(packageName, fingerprint.copyOf(), payload.copyOf()))
    }
}
