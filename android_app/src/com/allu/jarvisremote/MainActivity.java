package com.allu.jarvisremote;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.view.KeyEvent;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {

    private static final String PREFS_NAME = "jarvis_remote_prefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String DEFAULT_URL = "http://10.233.226.213:8765";

    private WebView webView;
    private SharedPreferences prefs;
    private Vibrator vibrator;
    private Handler mainHandler;
    private String currentServerUrl;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Edge-to-Edge System Bar Polish
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        window.clearFlags(WindowManager.LayoutParams.FLAG_TRANSLUCENT_STATUS);
        window.setStatusBarColor(Color.parseColor("#040507"));
        window.setNavigationBarColor(Color.parseColor("#040507"));

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            window.getAttributes().layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }

        mainHandler = new Handler(Looper.getMainLooper());
        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
        currentServerUrl = prefs.getString(KEY_SERVER_URL, DEFAULT_URL);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#040507"));

        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#040507"));
        setupWebView();
        root.addView(webView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        setContentView(root);

        // Load 4K Bespoke Native HUD UI from APK Assets
        webView.loadUrl("file:///android_asset/index.html");
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadsImagesAutomatically(true);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(false);
        settings.setDisplayZoomControls(false);
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);

        // Allow file:///android_asset to fetch LAN endpoints seamlessly
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        try {
            settings.setAllowFileAccessFromFileURLs(true);
            settings.setAllowUniversalAccessFromFileURLs(true);
        } catch (Exception ignored) {}

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.JELLY_BEAN_MR1) {
            settings.setMediaPlaybackRequiresUserGesture(false);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        webView.addJavascriptInterface(new WebAppInterface(), "AndroidBridge");

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                if (url.startsWith("file://") || url.startsWith("http://") || url.startsWith("https://")) {
                    view.loadUrl(url);
                    return true;
                }
                return false;
            }
        });

        webView.setWebChromeClient(new WebChromeClient());
    }

    public void promptChangeServerIp() {
        mainHandler.post(() -> {
            AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
            builder.setTitle("JARVIS PC Server URL");

            final EditText input = new EditText(this);
            input.setText(currentServerUrl);
            input.setHint("http://192.168.1.xxx:8765");
            input.setPadding(40, 30, 40, 30);
            builder.setView(input);

            builder.setPositiveButton("Connect", (dialog, which) -> {
                String newUrl = input.getText().toString().trim();
                if (!newUrl.startsWith("http://") && !newUrl.startsWith("https://")) {
                    newUrl = "http://" + newUrl;
                }
                if (!newUrl.contains(":8765")) {
                    newUrl = newUrl + ":8765";
                }
                if (newUrl.endsWith("/")) {
                    newUrl = newUrl.substring(0, newUrl.length() - 1);
                }
                if (newUrl.endsWith("/remote")) {
                    newUrl = newUrl.substring(0, newUrl.length() - "/remote".length());
                }
                currentServerUrl = newUrl;
                prefs.edit().putString(KEY_SERVER_URL, newUrl).apply();

                // Notify frontend
                webView.evaluateJavascript("window.onServerIpUpdated && window.onServerIpUpdated('" + newUrl + "');", null);
            });
            builder.setNegativeButton("Cancel", (dialog, which) -> dialog.cancel());
            builder.show();
        });
    }

    private void sendPcVolumeCommand(final String action) {
        new Thread(() -> {
            try {
                String baseUrl = currentServerUrl;
                URL url = new URL(baseUrl + "/api/command");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                conn.setConnectTimeout(1500);
                conn.setReadTimeout(1500);

                String json = "{\"command\":\"" + action + "\"}";
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(json.getBytes("UTF-8"));
                }
                conn.getResponseCode();
                conn.disconnect();
            } catch (Exception ignored) {}
        }).start();
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_VOLUME_UP) {
            sendPcVolumeCommand("volume_up");
            triggerHaptic(25);
            webView.evaluateJavascript("window.onNativeVolumeKey && window.onNativeVolumeKey('up');", null);
            return true;
        } else if (keyCode == KeyEvent.KEYCODE_VOLUME_DOWN) {
            sendPcVolumeCommand("volume_down");
            triggerHaptic(25);
            webView.evaluateJavascript("window.onNativeVolumeKey && window.onNativeVolumeKey('down');", null);
            return true;
        } else if (keyCode == KeyEvent.KEYCODE_BACK) {
            webView.evaluateJavascript("window.onNativeBackPressed ? window.onNativeBackPressed() : false;", value -> {
                if (!"true".equals(value)) {
                    finish();
                }
            });
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    private void triggerHaptic(int ms) {
        if (vibrator != null) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                vibrator.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE));
            } else {
                vibrator.vibrate(ms);
            }
        }
    }

    public class WebAppInterface {
        @JavascriptInterface
        public String getServerIp() {
            return currentServerUrl;
        }

        @JavascriptInterface
        public void setServerIp(String url) {
            currentServerUrl = url;
            prefs.edit().putString(KEY_SERVER_URL, url).apply();
        }

        @JavascriptInterface
        public void vibrate(int ms) {
            triggerHaptic(ms);
        }

        @JavascriptInterface
        public void vibrateFeedback(String type) {
            if ("light".equals(type)) {
                triggerHaptic(15);
            } else if ("medium".equals(type)) {
                triggerHaptic(35);
            } else if ("heavy".equals(type)) {
                triggerHaptic(60);
            } else if ("success".equals(type)) {
                new Thread(() -> {
                    triggerHaptic(20);
                    try { Thread.sleep(60); } catch (Exception ignored) {}
                    triggerHaptic(40);
                }).start();
            } else {
                triggerHaptic(25);
            }
        }

        @JavascriptInterface
        public void keepScreenOn(boolean keep) {
            mainHandler.post(() -> {
                if (keep) {
                    getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                } else {
                    getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
                }
            });
        }

        @JavascriptInterface
        public void promptChangeIp() {
            promptChangeServerIp();
        }

        @JavascriptInterface
        public boolean isNativeApp() {
            return true;
        }

        @JavascriptInterface
        public String getNativeVersion() {
            return "2.0.0 Pro 4K (Android 14/15)";
        }
    }
}