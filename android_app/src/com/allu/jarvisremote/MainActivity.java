package com.allu.jarvisremote;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.ClipData;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ProgressBar;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;

public class MainActivity extends Activity {

    private static final String PREFS_NAME = "jarvis_remote_prefs";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String DEFAULT_URL = "http://10.233.226.213:8765/remote";
    private static final int FILE_CHOOSER_REQUEST_CODE = 2001;
    private static final int PERMISSION_REQUEST_MIC = 3001;
    private static final int SPEECH_REQUEST_CODE = 4001;

    private WebView webView;
    private ProgressBar progressBar;
    private TextView settingsPill;
    private SharedPreferences prefs;
    private Vibrator vibrator;
    private Handler mainHandler;
    private String currentServerUrl;
    private ValueCallback<Uri[]> mFilePathCallback;
    private SpeechRecognizer speechRecognizer;
    private boolean isListeningSpeech = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Modern Edge-to-Edge System Bars
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        window.clearFlags(WindowManager.LayoutParams.FLAG_TRANSLUCENT_STATUS);
        window.setStatusBarColor(Color.parseColor("#060609"));
        window.setNavigationBarColor(Color.parseColor("#060609"));

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) {
            window.getAttributes().layoutInDisplayCutoutMode =
                    WindowManager.LayoutParams.LAYOUT_IN_DISPLAY_CUTOUT_MODE_SHORT_EDGES;
        }

        mainHandler = new Handler(Looper.getMainLooper());
        prefs = getSharedPreferences(PREFS_NAME, MODE_PRIVATE);
        vibrator = (Vibrator) getSystemService(Context.VIBRATOR_SERVICE);
        currentServerUrl = prefs.getString(KEY_SERVER_URL, DEFAULT_URL);

        // Request Microphone runtime permission for Voice Memo and Dictation
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, PERMISSION_REQUEST_MIC);
            }
        }

        initNativeSpeechRecognizer();

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(Color.parseColor("#060609"));

        // 1. Fullscreen Modern WebView
        webView = new WebView(this);
        webView.setBackgroundColor(Color.parseColor("#060609"));
        setupWebView();
        root.addView(webView, new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT,
                FrameLayout.LayoutParams.MATCH_PARENT));

        // 2. High-Tech Top Progress Glow Line
        progressBar = new ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal);
        progressBar.setMax(100);
        progressBar.setProgress(0);
        progressBar.setVisibility(View.GONE);
        FrameLayout.LayoutParams pbLp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.MATCH_PARENT, 6);
        pbLp.gravity = Gravity.TOP;
        root.addView(progressBar, pbLp);

        // 3. Subtle Quick Settings Pill (top-right corner)
        settingsPill = new TextView(this);
        settingsPill.setText("\u2699 IP");
        settingsPill.setTextColor(Color.parseColor("#8E8E93"));
        settingsPill.setTextSize(11);
        settingsPill.setPadding(26, 12, 26, 12);
        GradientDrawable pillBg = new GradientDrawable();
        pillBg.setColor(Color.parseColor("#5514141e"));
        pillBg.setCornerRadius(30);
        pillBg.setStroke(2, Color.parseColor("#25FFFFFF"));
        settingsPill.setBackground(pillBg);
        settingsPill.setAlpha(0.40f);

        FrameLayout.LayoutParams pillLp = new FrameLayout.LayoutParams(
                FrameLayout.LayoutParams.WRAP_CONTENT,
                FrameLayout.LayoutParams.WRAP_CONTENT);
        pillLp.gravity = Gravity.TOP | Gravity.END;
        pillLp.setMargins(0, 36, 24, 0);
        settingsPill.setLayoutParams(pillLp);
        settingsPill.setOnClickListener(v -> promptChangeServerIp());
        root.addView(settingsPill);

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
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);

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
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                progressBar.setVisibility(View.GONE);
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) {
                    showConnectionErrorPage();
                }
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                progressBar.setProgress(newProgress);
                if (newProgress < 100) {
                    progressBar.setVisibility(View.VISIBLE);
                } else {
                    progressBar.setVisibility(View.GONE);
                }
            }

            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                mainHandler.post(() -> {
                    try {
                        request.grant(request.getResources());
                    } catch (Exception ignored) {}
                });
            }

            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, FileChooserParams fileChooserParams) {
                if (mFilePathCallback != null) {
                    mFilePathCallback.onReceiveValue(null);
                    mFilePathCallback = null;
                }
                mFilePathCallback = filePathCallback;

                Intent intent = null;
                if (fileChooserParams != null) {
                    try {
                        intent = fileChooserParams.createIntent();
                    } catch (Exception ignored) {}
                }
                if (intent == null) {
                    intent = new Intent(Intent.ACTION_GET_CONTENT);
                    intent.addCategory(Intent.CATEGORY_OPENABLE);
                    intent.setType("*/*");
                    intent.putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true);
                }
                try {
                    startActivityForResult(Intent.createChooser(intent, "Choose Files to Send"), FILE_CHOOSER_REQUEST_CODE);
                    return true;
                } catch (ActivityNotFoundException e) {
                    if (mFilePathCallback != null) {
                        mFilePathCallback.onReceiveValue(null);
                        mFilePathCallback = null;
                    }
                    return false;
                }
            }
        });
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER_REQUEST_CODE) {
            if (mFilePathCallback != null) {
                Uri[] results = null;
                if (resultCode == Activity.RESULT_OK && data != null) {
                    ClipData clipData = data.getClipData();
                    if (clipData != null) {
                        int count = clipData.getItemCount();
                        results = new Uri[count];
                        for (int i = 0; i < count; i++) {
                            results[i] = clipData.getItemAt(i).getUri();
                        }
                    } else if (data.getData() != null) {
                        results = new Uri[]{ data.getData() };
                    }
                }
                mFilePathCallback.onReceiveValue(results);
                mFilePathCallback = null;
            }
        } else if (requestCode == SPEECH_REQUEST_CODE && resultCode == Activity.RESULT_OK && data != null) {
            ArrayList<String> matches = data.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS);
            if (matches != null && !matches.isEmpty()) {
                String spokenText = matches.get(0);
                sendPcDictation(spokenText);
                String quoted = JSONObject.quote(spokenText);
                webView.evaluateJavascript("if (window.onNativeDictationResult) { window.onNativeDictationResult(" + quoted + "); }", null);
            }
        }
    }

    private void initNativeSpeechRecognizer() {
        mainHandler.post(() -> {
            try {
                if (SpeechRecognizer.isRecognitionAvailable(this)) {
                    if (speechRecognizer != null) {
                        try {
                            speechRecognizer.destroy();
                        } catch (Exception ignored) {}
                    }
                    speechRecognizer = SpeechRecognizer.createSpeechRecognizer(this);
                    speechRecognizer.setRecognitionListener(new RecognitionListener() {
                        @Override
                        public void onReadyForSpeech(Bundle params) {
                            isListeningSpeech = true;
                            notifyWebSpeechStatus("ready", "");
                        }

                        @Override
                        public void onBeginningOfSpeech() {
                            notifyWebSpeechStatus("speaking", "");
                        }

                        @Override
                        public void onRmsChanged(float rmsdB) {}

                        @Override
                        public void onBufferReceived(byte[] buffer) {}

                        @Override
                        public void onEndOfSpeech() {
                            notifyWebSpeechStatus("processing", "");
                        }

                        @Override
                        public void onError(int error) {
                            isListeningSpeech = false;
                            String msg = "Speech error " + error;
                            if (error == SpeechRecognizer.ERROR_NO_MATCH) msg = "No speech detected";
                            else if (error == SpeechRecognizer.ERROR_SPEECH_TIMEOUT) msg = "Speech timeout";
                            notifyWebSpeechStatus("error", msg);
                        }

                        @Override
                        public void onResults(Bundle results) {
                            isListeningSpeech = false;
                            ArrayList<String> matches = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                            if (matches != null && !matches.isEmpty()) {
                                String spokenText = matches.get(0).trim();
                                if (!spokenText.isEmpty()) {
                                    sendPcDictation(spokenText);
                                    String quoted = JSONObject.quote(spokenText);
                                    webView.evaluateJavascript("if (window.onNativeDictationResult) { window.onNativeDictationResult(" + quoted + "); }", null);
                                }
                            }
                            notifyWebSpeechStatus("done", "");
                        }

                        @Override
                        public void onPartialResults(Bundle partialResults) {
                            ArrayList<String> matches = partialResults.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
                            if (matches != null && !matches.isEmpty()) {
                                String partialText = matches.get(0).trim();
                                if (!partialText.isEmpty()) {
                                    String quoted = JSONObject.quote(partialText);
                                    webView.evaluateJavascript("if (window.onNativePartialSpeech) { window.onNativePartialSpeech(" + quoted + "); }", null);
                                }
                            }
                        }

                        @Override
                        public void onEvent(int eventType, Bundle params) {}
                    });
                }
            } catch (Exception ignored) {}
        });
    }

    private void notifyWebSpeechStatus(String state, String detail) {
        mainHandler.post(() -> {
            if (webView != null) {
                String sQ = JSONObject.quote(state);
                String dQ = JSONObject.quote(detail);
                webView.evaluateJavascript("if (window.onNativeSpeechState) { window.onNativeSpeechState(" + sQ + ", " + dQ + "); }", null);
            }
        });
    }

    public void startNativeSpeechListening() {
        mainHandler.post(() -> {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, PERMISSION_REQUEST_MIC);
                    return;
                }
            }

            if (speechRecognizer == null) {
                initNativeSpeechRecognizer();
            }

            if (speechRecognizer != null) {
                try {
                    Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
                    intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
                    intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true);
                    intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 750L);
                    intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 750L);
                    intent.putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 1500L);
                    intent.putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3);
                    speechRecognizer.startListening(intent);
                    isListeningSpeech = true;
                    notifyWebSpeechStatus("starting", "");
                    return;
                } catch (Exception ignored) {}
            }

            // Fallback to standard RecognizerIntent dialog if SpeechRecognizer is unavailable on this device
            try {
                Intent intent = new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH);
                intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM);
                intent.putExtra(RecognizerIntent.EXTRA_PROMPT, "Speak now to type live on PC...");
                startActivityForResult(intent, SPEECH_REQUEST_CODE);
            } catch (ActivityNotFoundException e) {
                webView.evaluateJavascript("alert('Speech recognition is not available on this device');", null);
            }
        });
    }

    public void stopNativeSpeechListening() {
        mainHandler.post(() -> {
            if (speechRecognizer != null && isListeningSpeech) {
                try {
                    speechRecognizer.stopListening();
                } catch (Exception ignored) {}
            }
        });
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQUEST_MIC) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                initNativeSpeechRecognizer();
                startNativeSpeechListening();
            }
        }
    }

    @Override
    protected void onDestroy() {
        if (speechRecognizer != null) {
            try {
                speechRecognizer.destroy();
                speechRecognizer = null;
            } catch (Exception ignored) {}
        }
        super.onDestroy();
    }

    private void sendPcDictation(final String text) {
        new Thread(() -> {
            try {
                String baseUrl = currentServerUrl;
                int idx = baseUrl.indexOf("/remote");
                if (idx != -1) baseUrl = baseUrl.substring(0, idx);
                URL url = new URL(baseUrl + "/api/mic/dictate");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                conn.setConnectTimeout(2500);
                conn.setReadTimeout(2500);

                JSONObject json = new JSONObject();
                json.put("text", text);
                json.put("mode", "paste");
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(json.toString().getBytes("UTF-8"));
                }
                conn.getResponseCode();
                conn.disconnect();
            } catch (Exception ignored) {}
        }).start();
    }

    private void loadServerUrl(String url) {
        currentServerUrl = url;
        prefs.edit().putString(KEY_SERVER_URL, url).apply();
        progressBar.setVisibility(View.VISIBLE);
        webView.loadUrl(url);
    }

    private void showConnectionErrorPage() {
        String html = "<!DOCTYPE html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'>"
                + "<style>"
                + "body{background:#000000;color:#ffffff;font-family:-apple-system,BlinkMacSystemFont,sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:100vh;margin:0;padding:24px;box-sizing:border-box;text-align:center;}"
                + ".card{background:rgba(28,28,30,0.85);border:1px solid rgba(255,255,255,0.12);border-radius:24px;padding:32px 24px;max-width:360px;width:100%;box-shadow:0 20px 40px rgba(0,0,0,0.6);backdrop-filter:blur(30px);}"
                + ".glow-dot{width:48px;height:48px;border-radius:50%;background:linear-gradient(135deg,#007aff,#00d2ff);margin:0 auto 16px;display:flex;align-items:center;justify-content:center;box-shadow:0 0 24px rgba(0,210,255,0.5);}"
                + "h2{font-size:20px;font-weight:700;margin:0 0 6px;letter-spacing:-0.4px;}"
                + ".badge{display:inline-block;padding:3px 10px;border-radius:12px;background:rgba(250,45,72,0.18);border:0.5px solid rgba(250,45,72,0.4);color:#fa2d48;font-size:11px;font-weight:700;margin-bottom:16px;}"
                + "p{color:rgba(255,255,255,0.6);font-size:13px;line-height:1.5;margin:0 0 16px;}"
                + ".target{background:rgba(255,255,255,0.06);padding:8px 12px;border-radius:10px;font-family:monospace;font-size:12px;color:#00d2ff;word-break:break-all;margin-bottom:20px;display:block;}"
                + ".btn{display:block;width:100%;background:#007aff;color:#ffffff;border:none;padding:14px;border-radius:14px;font-size:15px;font-weight:700;cursor:pointer;margin-bottom:10px;transition:0.2s;box-sizing:border-box;}"
                + ".btn:active{transform:scale(0.98);opacity:0.9;}"
                + ".btn.sec{background:rgba(255,255,255,0.12);color:#ffffff;}"
                + "</style></head><body>"
                + "<div class='card'>"
                + "<div class='glow-dot'><svg width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='#fff' stroke-width='2.2'><polygon points='13 2 3 14 12 14 11 22 21 10 12 10 13 2'></polygon></svg></div>"
                + "<h2>JARVIS Remote Pro</h2>"
                + "<div class='badge'>Disconnected</div>"
                + "<p>Make sure your PC Desktop Pet server is running and both devices are connected to the same Wi-Fi.</p>"
                + "<span class='target'>" + currentServerUrl + "</span>"
                + "<button class='btn' onclick='location.reload()'>&#x26A1; Reconnect Now</button>"
                + "<button class='btn sec' onclick='window.AndroidBridge.promptChangeIp()'>&#x2699;&#xFE0F; Change Server IP</button>"
                + "</div></body></html>";
        webView.loadDataWithBaseURL(null, html, "text/html", "UTF-8", null);
    }

    public void promptChangeServerIp() {
        mainHandler.post(() -> {
            AlertDialog.Builder builder = new AlertDialog.Builder(this, android.R.style.Theme_DeviceDefault_Dialog_Alert);
            builder.setTitle("JARVIS PC Server URL");

            final EditText input = new EditText(this);
            input.setText(currentServerUrl);
            input.setHint("http://192.168.1.xxx:8765/remote");
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
            if (vibrator != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createOneShot(20, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    vibrator.vibrate(20);
                }
            }
            return true;
        } else if (keyCode == KeyEvent.KEYCODE_VOLUME_DOWN) {
            sendPcVolumeCommand("volume_down");
            if (vibrator != null) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    vibrator.vibrate(VibrationEffect.createOneShot(20, VibrationEffect.DEFAULT_AMPLITUDE));
                } else {
                    vibrator.vibrate(20);
                }
            }
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
            return "2.3.0 Pro (Streaming Speech & Win32 Direct Input)";
        }

        @JavascriptInterface
        public void startNativeDictation() {
            startNativeSpeechListening();
        }

        @JavascriptInterface
        public void stopNativeDictation() {
            stopNativeSpeechListening();
        }

        @JavascriptInterface
        public int getBatteryLevel() {
            try {
                BatteryManager bm = (BatteryManager) getSystemService(Context.BATTERY_SERVICE);
                if (bm != null) {
                    int cap = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
                    if (cap >= 0 && cap <= 100) return cap;
                }
                IntentFilter ifilter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
                Intent b = registerReceiver(null, ifilter);
                if (b != null) {
                    int level = b.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
                    int scale = b.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
                    if (level >= 0 && scale > 0) {
                        return Math.round((level / (float) scale) * 100);
                    }
                }
            } catch (Exception ignored) {}
            return -1;
        }

        @JavascriptInterface
        public boolean isCharging() {
            try {
                IntentFilter ifilter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
                Intent b = registerReceiver(null, ifilter);
                if (b != null) {
                    int status = b.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
                    return status == BatteryManager.BATTERY_STATUS_CHARGING || status == BatteryManager.BATTERY_STATUS_FULL;
                }
            } catch (Exception ignored) {}
            return false;
        }

        @JavascriptInterface
        public void triggerNativeFilePicker() {
            mainHandler.post(() -> {
                if (webView != null) {
                    webView.evaluateJavascript("document.getElementById('upload-input') && document.getElementById('upload-input').click();", null);
                }
            });
        }
    }
}