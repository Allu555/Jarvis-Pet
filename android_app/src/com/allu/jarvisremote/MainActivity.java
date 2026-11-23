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
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.Toast;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class MainActivity extends Activity {

    private static final String PREFS_NAME = "jarvis_remote_prefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String DEFAULT_URL = "http://10.233.226.213:8765/remote";

    private WebView webView;
    private SharedPreferences prefs;
    private Vibrator vibrator;
    private Handler mainHandler;
    private String currentServerUrl;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        requestWindowFeature(Window.FEATURE_NO_TITLE);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_FULLSCREEN, WindowManager.LayoutParams.FLAG_FULLSCREEN);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            getWindow().setStatusBarColor(Color.BLACK);
            getWindow().setNavigationBarColor(Color.BLACK);
        }

        mainHandler = new Handler(Looper.getMainLooper());
        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
        currentServerUrl = prefs.getString(KEY_SERVER_URL, DEFAULT_URL);

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.BLACK);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.BLACK);
        setupWebView();

        root.addView(webView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        setContentView(root);
        loadServerUrl(currentServerUrl);
    }

    private void setupWebView() {
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadsImagesAutomatically(true);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);

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
                view.loadUrl(url);
                return true;
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    showConnectionErrorPage();
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient());
    }

    private void loadServerUrl(String url) {
        currentServerUrl = url;
        prefs.edit().putString(KEY_SERVER_URL, url).apply();
        webView.loadUrl(url);
    }

    private void showConnectionErrorPage() {
        String html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
                + "<style>body{background:#0a0a0e;color:#fff;font-family:sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center;padding:24px;box-sizing:border-box;}"
                + "h2{color:#fa2d48;margin-bottom:8px;}p{color:rgba(255,255,255,0.6);font-size:14px;margin-bottom:24px;line-height:1.5;}"
                + ".btn{background:#007aff;color:#fff;border:none;padding:12px 24px;border-radius:12px;font-size:15px;font-weight:700;margin:6px;cursor:pointer;width:200px;}"
                + ".btn.sec{background:rgba(255,255,255,0.15);}</style></head><body>"
                + "<h2>Cannot Connect to PC</h2>"
                + "<p>Make sure your PC Desktop Pet server is running and both devices are on the same Wi-Fi.<br><br>Target: " + currentServerUrl + "</p>"
                + "<button class='btn' onclick='location.reload()'>&#x1F504; Retry</button><br>"
                + "<button class='btn sec' onclick='window.AndroidBridge.promptChangeIp()'>&#x2699;&#xFE0F; Change Server IP</button>"
                + "</body></html>";
        webView.loadDataWithBaseURL(null, html, "text/html", "UTF-8", null);
    }

    public void promptChangeServerIp() {
        mainHandler.post(() -> {
            AlertDialog.Builder builder = new AlertDialog.Builder(this);
            builder.setTitle("JARVIS PC Server URL");

            final EditText input = new EditText(this);
            input.setText(currentServerUrl);
            input.setHint("http://192.168.1.xxx:8765/remote");
            builder.setView(input);

            builder.setPositiveButton("Connect", (dialog, which) -> {
                String newUrl = input.getText().toString().trim();
                if (!newUrl.startsWith("http://") && !newUrl.startsWith("https://")) {
                    newUrl = "http://" + newUrl;
                }
                if (!newUrl.contains(":8765")) {
                    newUrl = newUrl + ":8765";
                }
                if (!newUrl.endsWith("/remote")) {
                    newUrl = newUrl + "/remote";
                }
                loadServerUrl(newUrl);
            });
            builder.setNegativeButton("Cancel", (dialog, which) -> dialog.cancel());
            builder.show();
        });
    }

    private void sendPcVolumeCommand(final String action) {
        new Thread(() -> {
            try {
                String baseUrl = currentServerUrl;
                int idx = baseUrl.indexOf("/remote");
                if (idx != -1) baseUrl = baseUrl.substring(0, idx);
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
            if (vibrator != null) vibrator.vibrate(20);
            return true;
        } else if (keyCode == KeyEvent.KEYCODE_VOLUME_DOWN) {
            sendPcVolumeCommand("volume_down");
            if (vibrator != null) vibrator.vibrate(20);
            return true;
        } else if (keyCode == KeyEvent.KEYCODE_BACK) {
            if (webView.canGoBack()) {
                webView.goBack();
                return true;
            }
        }
        return super.onKeyDown(keyCode, event);
    }

    public class WebAppInterface {
        @JavascriptInterface
        public void vibrate(int ms) {
            if (vibrator != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    vibrator.vibrate(ms);
                }
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
            return "1.0.0 (Native Android)";
        }
    }
}
