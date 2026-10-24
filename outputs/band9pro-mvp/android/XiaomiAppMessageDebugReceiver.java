/*  Copyright (C) 2026

    This file is part of Gadgetbridge.

    Gadgetbridge is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Gadgetbridge is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>. */
package nodomain.freeyourgadget.gadgetbridge.externalevents;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.location.Criteria;
import android.location.Location;
import android.location.LocationManager;
import android.net.Uri;
import android.util.Base64;

import androidx.core.app.ActivityCompat;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileInputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Collections;

import kotlin.Unit;

import nodomain.freeyourgadget.gadgetbridge.service.devices.xiaomi.XiaomiSupport;
import nodomain.freeyourgadget.gadgetbridge.util.InternetUtils;

/**
 * Debug-only receiver for exercising XiaomiRpkService's third-party app messaging
 * (see CMD_RPK_APP_MESSAGE_TO_WATCH). Not wired into any real feature yet — this is
 * a manual test harness, triggered via:
 *
 *   adb shell am broadcast \
 *     -a nodomain.freeyourgadget.gadgetbridge.ACTION_SEND_APP_MESSAGE \
 *     --es package dev.notes.band9prointerconnect \
 *     --es message "hello from phone"
 *
 * If the "message" extra is omitted, fetches the phone's public IP from the real
 * internet and sends that instead, as a concrete demonstration of relaying
 * internet-fetched content to a watch app that has no network access of its own.
 *
 * Also registers a persistent AppMessageListener (see below) so that any watch app
 * sending a "FIX:<lat>,<lon>" message gets a real OpenStreetMap tile fetched and
 * relayed back — this is what dev.notes.band9prolocation ("Location") uses to
 * render an actual map tile around the device's own GPS fix.
 */
public class XiaomiAppMessageDebugReceiver extends BroadcastReceiver {
    private static final Logger LOG = LoggerFactory.getLogger(XiaomiAppMessageDebugReceiver.class);

    public static final String ACTION_SEND_APP_MESSAGE = "nodomain.freeyourgadget.gadgetbridge.ACTION_SEND_APP_MESSAGE";
    public static final String ACTION_CONFIGURE_BAND_AGENT = "nodomain.freeyourgadget.gadgetbridge.ACTION_CONFIGURE_BAND_AGENT";

    private static final int TILE_ZOOM = 16;

    @Override
    public void onReceive(final Context context, final Intent intent) {
        if (intent == null) {
            return;
        }

        if (ACTION_CONFIGURE_BAND_AGENT.equals(intent.getAction())) {
            context.getSharedPreferences("band_agent", Context.MODE_PRIVATE).edit()
                    .putString("api_url", intent.getStringExtra("api_url"))
                    .putString("phone_token", intent.getStringExtra("phone_token"))
                    .apply();
            return;
        }
        if (!ACTION_SEND_APP_MESSAGE.equals(intent.getAction())) return;

        final String packageName = intent.getStringExtra("package");
        if (packageName == null || packageName.isEmpty()) {
            LOG.warn("XiaomiAppMessageDebugReceiver: no 'package' extra provided");
            return;
        }

        final XiaomiSupport support = XiaomiSupport.getActiveInstance();
        if (support == null) {
            LOG.warn("XiaomiAppMessageDebugReceiver: no active XiaomiSupport instance (device not connected?)");
            return;
        }

        // Idempotent: (re-)registering on every debug broadcast keeps the tile
        // responder alive even after the phone-side process restarts and the
        // listener reference is lost (XiaomiRpkService is recreated per connection).
        support.getRpkService().setAppMessageListener(
                (fromPackage, message) -> handleIncomingAppMessage(context, support, fromPackage, message));

        final String explicitMessage = intent.getStringExtra("message");
        final String imagePath = intent.getStringExtra("imagePath");

        // A raw background Thread spawned from onReceive() can lose network access once
        // onReceive() returns (the OS may treat the component as done and restrict it).
        // goAsync() properly extends the receiver's lifetime until finish() is called.
        final PendingResult pendingResult = goAsync();

        new Thread(() -> {
            try {
                // The watch-side system.interconnect channel requires the app to be marked
                // "connected" (RpkAppStatus, subtype 7) before it will accept sendMessageToApp
                // (subtype 8) — mirrors the official app's launchApp() + sendMessageToWear()
                // sequence (MyService.java in Watchdrip-Xiaomi).
                LOG.debug("XiaomiAppMessageDebugReceiver: marking {} as connected", packageName);
                support.getRpkService().sendAppStatus(packageName, new byte[0], true);

                try {
                    Thread.sleep(500);
                } catch (final InterruptedException ignored) {
                }

                final String message;
                if (imagePath != null) {
                    message = "IMG:" + readFileAsBase64(imagePath);
                } else if (explicitMessage != null) {
                    message = explicitMessage;
                } else {
                    message = fetchPublicIp();
                }
                LOG.debug("XiaomiAppMessageDebugReceiver: sending to {}: {} bytes", packageName, message.length());
                support.getRpkService().sendMessageToApp(packageName, new byte[0], message.getBytes(StandardCharsets.UTF_8));
            } finally {
                pendingResult.finish();
            }
        }, "xiaomi-app-message-debug").start();
    }

    private void handleIncomingAppMessage(final Context context, final XiaomiSupport support,
                                           final String fromPackage, final byte[] message) {
        final String raw = new String(message, StandardCharsets.UTF_8);
        // The watch-side conn.send({ data: { data: '...' } }) API wraps the actual
        // payload in a JSON envelope on the wire — the raw bytes we get here are
        // literally {"data":"..."}, not the bare string.
        final String text;
        try {
            text = new org.json.JSONObject(raw).optString("data", raw);
        } catch (final org.json.JSONException e) {
            LOG.warn("XiaomiAppMessageDebugReceiver: failed to parse incoming message envelope: {}", raw, e);
            return;
        }
        LOG.debug("XiaomiAppMessageDebugReceiver: unwrapped message from {}: {}", fromPackage, text);
        forwardBandAgentInteraction(context, text);
        if (!text.startsWith("FIX:")) {
            return;
        }

        final String payload = text.substring(4);

        if ("PHONE".equals(payload)) {
            // The watch has no GPS fix of its own (e.g. indoors) — fall back to the
            // phone's own last-known location (Gadgetbridge already holds
            // ACCESS_FINE/COARSE_LOCATION for BLE scanning purposes).
            final Location phoneLocation = getPhoneLastKnownLocation(context);
            if (phoneLocation == null) {
                LOG.warn("XiaomiAppMessageDebugReceiver: no phone location available for fallback");
                return;
            }
            LOG.debug("XiaomiAppMessageDebugReceiver: using phone location as fallback: {}, {}",
                    phoneLocation.getLatitude(), phoneLocation.getLongitude());
            new Thread(() -> fetchAndSendTile(context, support, fromPackage,
                    phoneLocation.getLatitude(), phoneLocation.getLongitude()), "xiaomi-tile-fetch").start();
            return;
        }

        final String[] parts = payload.split(",");
        if (parts.length != 2) {
            LOG.warn("XiaomiAppMessageDebugReceiver: malformed FIX message: {}", text);
            return;
        }

        final double lat;
        final double lon;
        try {
            lat = Double.parseDouble(parts[0]);
            lon = Double.parseDouble(parts[1]);
        } catch (final NumberFormatException e) {
            LOG.warn("XiaomiAppMessageDebugReceiver: malformed FIX coordinates: {}", text);
            return;
        }

        new Thread(() -> fetchAndSendTile(context, support, fromPackage, lat, lon), "xiaomi-tile-fetch").start();
    }

    /** Forward watch choices to the user's local API without involving a cloud service. */
    private static void forwardBandAgentInteraction(final Context context, final String text) {
        try {
            final org.json.JSONObject message = new org.json.JSONObject(text);
            final String type = message.optString("type", "");
            if (!"option_selected".equals(type) && !"voice_request".equals(type)) return;
            final android.content.SharedPreferences prefs = context.getSharedPreferences("band_agent", Context.MODE_PRIVATE);
            final String api = prefs.getString("api_url", "");
            final String token = prefs.getString("phone_token", "");
            if (api.isEmpty() || token.isEmpty()) {
                LOG.debug("Band Agent API is not configured; retaining interaction in log");
                return;
            }
            new Thread(() -> {
                HttpURLConnection connection = null;
                try {
                    connection = (HttpURLConnection) new URL(api.replaceAll("/$", "") + "/v1/interactions").openConnection();
                    connection.setRequestMethod("POST");
                    connection.setConnectTimeout(5000);
                    connection.setReadTimeout(5000);
                    connection.setDoOutput(true);
                    connection.setRequestProperty("Authorization", "Bearer " + token);
                    connection.setRequestProperty("Content-Type", "application/json");
                    final byte[] body = message.toString().getBytes(StandardCharsets.UTF_8);
                    try (OutputStream output = connection.getOutputStream()) { output.write(body); }
                    LOG.debug("Band Agent interaction POST returned {}", connection.getResponseCode());
                } catch (Exception error) {
                    LOG.warn("Band Agent interaction POST failed", error);
                } finally {
                    if (connection != null) connection.disconnect();
                }
            }, "band-agent-interaction-upload").start();
        } catch (org.json.JSONException ignored) {
            // Other RPK messages are intentionally ignored by this bridge.
        }
    }

    private Location getPhoneLastKnownLocation(final Context context) {
        if (ActivityCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED
                && ActivityCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            LOG.warn("XiaomiAppMessageDebugReceiver: no location permission granted");
            return null;
        }
        final LocationManager locationManager = (LocationManager) context.getSystemService(Context.LOCATION_SERVICE);
        if (locationManager == null) {
            return null;
        }
        final String provider = locationManager.getBestProvider(new Criteria(), true);
        if (provider == null) {
            LOG.warn("XiaomiAppMessageDebugReceiver: no enabled location provider");
            return null;
        }
        return locationManager.getLastKnownLocation(provider);
    }

    private void fetchAndSendTile(final Context context, final XiaomiSupport support,
                                   final String packageName, final double lat, final double lon) {
        final int n = 1 << TILE_ZOOM;
        final int tileX = (int) Math.floor((lon + 180.0) / 360.0 * n);
        final double latRad = Math.toRadians(lat);
        final int tileY = (int) Math.floor(
                (1.0 - Math.log(Math.tan(latRad) + 1.0 / Math.cos(latRad)) / Math.PI) / 2.0 * n);

        final Uri tileUri = Uri.parse("https://tile.openstreetmap.org/" + TILE_ZOOM + "/" + tileX + "/" + tileY + ".png");
        final File targetFile = new File(context.getCacheDir(), "map-tile-" + TILE_ZOOM + "-" + tileX + "-" + tileY + ".png");

        LOG.debug("XiaomiAppMessageDebugReceiver: fetching tile {} for lat={}, lon={}", tileUri, lat, lon);
        InternetUtils.Companion.downloadBinaryFile(tileUri, targetFile, file -> {
            LOG.debug("XiaomiAppMessageDebugReceiver: tile downloaded, {} bytes", file.length());
            final String base64 = readFileAsBase64(file.getAbsolutePath());
            support.getRpkService().sendMessageToApp(packageName, new byte[0],
                    ("IMG:" + base64).getBytes(StandardCharsets.UTF_8));
            return Unit.INSTANCE;
        });
    }

    private String readFileAsBase64(final String path) {
        final File file = new File(path);
        final byte[] bytes = new byte[(int) file.length()];
        try (FileInputStream in = new FileInputStream(file)) {
            int offset = 0;
            while (offset < bytes.length) {
                final int read = in.read(bytes, offset, bytes.length - offset);
                if (read < 0) {
                    break;
                }
                offset += read;
            }
            return Base64.encodeToString(bytes, Base64.NO_WRAP);
        } catch (final Exception e) {
            LOG.warn("XiaomiAppMessageDebugReceiver: failed to read image file {}", path, e);
            return "";
        }
    }

    private String fetchPublicIp() {
        // Gadgetbridge's main process has no real INTERNET permission by design — all
        // networking goes through InternetUtils, which transparently uses either a direct
        // OkHttp call (if hasDirectInternetAccess()) or the separate Internethelper
        // companion app (nodomain.freeyourgadget.internethelper, via AIDL) as a fallback.
        // A raw HttpURLConnection from this process fails with EPERM at the socket layer.
        try {
            final String ip = InternetUtils.Companion.doStringRequest(
                    Uri.parse("https://api.ipify.org?format=text"),
                    "GET",
                    Collections.emptyMap(),
                    null,
                    false
            );
            if (ip == null) {
                return "fetch failed: null response (is Internethelper installed?)";
            }
            return "public IP: " + ip.trim();
        } catch (final Exception e) {
            LOG.warn("XiaomiAppMessageDebugReceiver: failed to fetch public IP", e);
            return "fetch failed: " + e.getMessage();
        }
    }
}
