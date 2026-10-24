# Gadgetbridge integration patch

Apply `android/XiaomiAppMessageDebugReceiver.java` to the matching Gadgetbridge fork and add the `ACTION_CONFIGURE_BAND_AGENT` intent action. The receiver forwards `option_selected` and `voice_request` JSON to `/v1/interactions` when configured with `api_url` and `phone_token` shared preferences. The debug APK on the phone predates this forwarding change; rebuild it before using automatic Grok feedback.
