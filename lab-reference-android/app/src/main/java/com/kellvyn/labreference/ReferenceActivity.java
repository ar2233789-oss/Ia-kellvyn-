package com.kellvyn.labreference;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONObject;

/**
 * Lab-only WebView shell. This APK is never packaged or merged into the Kellvyn app.
 * It renders the approved web reference on the same PocoF6Virtual AVD and display
 * profile as the native candidate, so comparisons do not depend on a desktop browser.
 */
public final class ReferenceActivity extends Activity {
    private static final String TAG = "KellvynWebViewLab";
    private static final String REFERENCE_URL = "http://127.0.0.1:4173/";
    private final Handler handler = new Handler(Looper.getMainLooper());
    private WebView webView;
    private String requestedState = "main";
    private boolean pageReady = false;

    public final class LabBridge {
        @JavascriptInterface
        public void ready(String state, String details) {
            Log.i(TAG, "READY state=" + state + " details=" + details);
        }

        @JavascriptInterface
        public void failed(String state, String reason) {
            Log.e(TAG, "FAILED state=" + state + " reason=" + reason);
        }

        @JavascriptInterface
        public void console(String message) {
            Log.i(TAG, "WEB " + message);
        }
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestedState = getIntent().getStringExtra("lab_state");
        if (requestedState == null || requestedState.isBlank()) requestedState = "main";

        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        window.setStatusBarColor(Color.rgb(11, 20, 19));
        window.setNavigationBarColor(Color.rgb(8, 13, 17));
        window.getDecorView().setSystemUiVisibility(0);

        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(8, 13, 17));
        webView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setLoadWithOverviewMode(false);
        settings.setUseWideViewPort(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        settings.setMediaPlaybackRequiresUserGesture(false);
        webView.addJavascriptInterface(new LabBridge(), "KellvynLab");
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage message) {
                Log.i(TAG, "CONSOLE " + message.message() + " (" + message.sourceId() + ":" + message.lineNumber() + ")");
                return true;
            }
        });
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String host = request.getUrl().getHost();
                return host != null && !host.equals("127.0.0.1") && !host.equals("localhost");
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                if (!pageReady) {
                    pageReady = true;
                    handler.postDelayed(() -> applyRequestedState(), 1200L);
                }
            }
        });
        setContentView(webView);
        Log.i(TAG, "LOAD state=" + requestedState + " url=" + REFERENCE_URL);
        webView.loadUrl(REFERENCE_URL);
    }

    private void evaluate(String javascript) {
        webView.evaluateJavascript(javascript, value ->
                Log.i(TAG, "JS_RESULT state=" + requestedState + " value=" + value));
    }

    private void applyRequestedState() {
        if (isFinishing() || webView == null) return;
        String state = JSONObject.quote(requestedState);
        String script =
                "(function() {" +
                "const state=" + state + ";" +
                "const report=(ok,reason)=>{" +
                "const details=JSON.stringify({title:document.title,width:innerWidth,height:innerHeight,dpr:devicePixelRatio,scrollY,reason:reason||''});" +
                "if(ok) window.KellvynLab.ready(state,details); else window.KellvynLab.failed(state,reason||'unknown');" +
                "};" +
                "const clickByText=(text)=>Array.from(document.querySelectorAll('button')).find(b=>b.innerText.trim()===text);" +
                "const openSettings=()=>{const b=document.querySelector('button[aria-label=\"Configurações\"]');if(!b){report(false,'settings button missing');return false;}b.click();return true;};" +
                "const done=()=>report(true,'');" +
                "if(state==='main'){done();return 'main-ready';}" +
                "if(!openSettings())return 'settings-open-failed';" +
                "setTimeout(()=>{" +
                "if(state==='settings'){done();return;}" +
                "if(state==='gold-settings'||state==='gold-main'){" +
                "const gold=clickByText('Preto e Dourado');" +
                "if(!gold){report(false,'gold palette button missing');return;}" +
                "gold.scrollIntoView({block:'center'});gold.click();" +
                "setTimeout(()=>{" +
                "if(state==='gold-main'){" +
                "const close=document.querySelector('button[aria-label=\"Fechar\"]');" +
                "if(close)close.click();" +
                "}" +
                "setTimeout(done,700);" +
                "},500);" +
                "return;" +
                "}" +
                "if(state==='effects'){" +
                "const lightning=clickByText('Raios');" +
                "if(!lightning){report(false,'lightning effect button missing');return;}" +
                "lightning.scrollIntoView({block:'center'});" +
                "setTimeout(()=>{lightning.click();const close=document.querySelector('button[aria-label=\\\"Fechar\\\"]');if(close)close.click();setTimeout(done,700);},350);" +
                "return;" +
                "}" +
                "report(false,'unsupported lab state '+state);" +
                "},600);" +
                "return 'state-transition-started';" +
                "})()";
        evaluate(script);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        if (webView != null) {
            webView.removeJavascriptInterface("KellvynLab");
            webView.stopLoading();
            webView.loadUrl("about:blank");
            webView.destroy();
            webView = null;
        }
        super.onDestroy();
    }
}
