package dev.xiaomi.bandagent

import org.json.JSONArray
import org.json.JSONObject

/**
 * Small, transport-agnostic bridge for the Xiaomi third-party-app message.
 *
 * The Gadgetbridge/AstroBox layer owns Bluetooth. This class only validates
 * messages and hands UTF-8 JSON to that existing connection, so a second
 * Bluetooth owner is never created.
 */
class InterconnectBridge(
    private val packageName: String,
    private val sendToBand: (ByteArray) -> Unit,
    private val onVoiceRequest: (requestId: String) -> Unit = {},
    private val nowSeconds: () -> Long = { System.currentTimeMillis() / 1000L },
) {
    private data class Pending(val options: Set<String>, val expiresAt: Long)

    private val pending = LinkedHashMap<String, Pending>()

    fun sendQuestion(
        requestId: String,
        title: String,
        text: String,
        options: List<Pair<String, String>>,
        expiresAt: Long,
    ) {
        require(requestId.isNotBlank() && requestId.length <= 96)
        require(title.length <= 40 && text.length <= 240)
        require(options.isNotEmpty() && options.size <= 3)
        require(expiresAt > nowSeconds())
        val ids = options.map { it.first }.toSet()
        require(ids.size == options.size && ids.all { it.isNotBlank() && it.length <= 32 })
        require(options.all { it.second.isNotBlank() && it.second.length <= 60 })
        pending[requestId] = Pending(ids, expiresAt)

        val array = JSONArray()
        options.forEach { (id, label) ->
            array.put(JSONObject().put("id", id).put("text", label))
        }
        send(JSONObject()
            .put("type", "question")
            .put("request_id", requestId)
            .put("title", title)
            .put("text", text)
            .put("options", array)
            .put("expires_at", expiresAt)
            .toString())
    }

    fun onBandMessage(bytes: ByteArray) {
        require(bytes.size <= 4096) { "interconnect payload too large" }
        val message = JSONObject(String(bytes, Charsets.UTF_8))
        val type = message.optString("type")
        val requestId = message.getString("request_id")
        if (type == "voice_request") {
            require(pending.containsKey(requestId)) { "unknown request" }
            onVoiceRequest(requestId)
            return
        }
        require(type == "option_selected")
        val optionId = message.getString("option_id")
        val request = pending[requestId] ?: return
        if (nowSeconds() < request.expiresAt && request.options.contains(optionId)) {
            pending.remove(requestId)
            send(JSONObject()
                .put("type", "ack")
                .put("request_id", requestId)
                .put("text", "已提交")
                .toString())
            // The caller forwards requestId/optionId to the Grok API.
        }
    }

    private fun send(json: String) {
        sendToBand(json.toByteArray(Charsets.UTF_8))
    }
}
