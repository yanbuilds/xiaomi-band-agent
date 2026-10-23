package dev.xiaomi.bandagent

/**
 * Host-side orchestration boundary for an Android Worker.
 *
 * Gadgetbridge remains the only Bluetooth owner.  The concrete Android app
 * supplies an HTTPS implementation of [BridgeApi] and a persistent source of
 * already-verified activity files.  This class deliberately accepts parsed
 * JSON rather than auth keys or raw Bluetooth frames.
 */
class PhoneSyncCoordinator(
    private val api: BridgeApi,
    private val interconnect: InterconnectBridge,
    private val nowSeconds: () -> Long = { System.currentTimeMillis() / 1000L },
) {
    interface BridgeApi {
        fun submitSleep(eventJson: String)
        fun pendingNotifications(): List<Notification>
        fun markSubmitted(notificationId: String)
    }

    data class Notification(
        val id: String,
        val requestId: String,
        val title: String,
        val text: String,
        val options: List<Pair<String, String>>,
        val expiresAt: Long,
    )

    data class Report(val sleepSubmitted: Int, val notificationsSent: Int)

    /** Upload parsed events, then drain a bounded notification batch. */
    fun runOnce(parsedSleepEvents: List<String>, maxNotifications: Int = 10): Report {
        parsedSleepEvents.forEach(api::submitSleep)
        var sent = 0
        api.pendingNotifications().take(maxNotifications).forEach { item ->
            if (item.expiresAt <= nowSeconds()) {
                api.markSubmitted(item.id)
                return@forEach
            }
            interconnect.sendQuestion(
                requestId = item.requestId,
                title = item.title,
                text = item.text,
                options = item.options,
                expiresAt = item.expiresAt,
            )
            api.markSubmitted(item.id)
            sent++
        }
        return Report(parsedSleepEvents.size, sent)
    }
}
