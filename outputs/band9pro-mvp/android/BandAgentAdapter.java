// SPDX-License-Identifier: AGPL-3.0-or-later
// Integration source for a Gadgetbridge fork, NOT a standalone Android app.
// Audited against Gadgetbridge a0948ee1cbc2a870f91d313f8e37df5f524465f7.
package nodomain.freeyourgadget.gadgetbridge.service.devices.xiaomi;

import nodomain.freeyourgadget.gadgetbridge.GBApplication;
import nodomain.freeyourgadget.gadgetbridge.model.NotificationSpec;

public final class BandAgentAdapter {
    private final XiaomiSupport support;

    // Obtain the existing connected XiaomiSupport from the service integration;
    // do not instantiate a second Bluetooth owner.
    public BandAgentAdapter(XiaomiSupport support) {
        this.support = support;
    }

    public void syncPreservingHistory() {
        // Must be enabled BEFORE fetching: upstream otherwise ACKs before parsing.
        boolean saved = GBApplication.getDeviceSpecificSharedPrefs(
                support.getDevice().getAddress()).edit()
                .putBoolean("keep_activity_data_on_device", true).commit();
        if (!saved) throw new IllegalStateException("Cannot persist retention setting");
        support.getConnectionSpecificSupport().runOnQueue("agent history sync",
                () -> support.onFetchRecordedData(0));
    }

    public void notifyAgent(int persistedNotificationId, String title, String body) {
        if (title == null || body == null || title.length() > 40 || body.length() > 400)
            throw new IllegalArgumentException("Invalid notification text");
        NotificationSpec n = new NotificationSpec(persistedNotificationId);
        n.sourceAppId = support.getContext().getPackageName();
        n.sourceName = "Sleep Agent";
        n.title = title;
        n.body = body;
        // No key/openOnPhone until a real Android notification/PendingIntent exists.
        support.getConnectionSpecificSupport().runOnQueue("agent notification",
                () -> support.onNotification(n));
    }

    // Diagnostic only: displays find-watch UI, not a programmable vibration API.
    // Caller must schedule stopFindDiagnostic() after a short bounded timeout,
    // and on cancellation. Do not automatically run this for every notification.
    public void startFindDiagnostic() {
        support.getConnectionSpecificSupport().runOnQueue("agent find start",
                () -> support.onFindDevice(true));
    }

    public void stopFindDiagnostic() {
        support.getConnectionSpecificSupport().runOnQueue("agent find stop",
                () -> support.onFindDevice(false));
    }
}
