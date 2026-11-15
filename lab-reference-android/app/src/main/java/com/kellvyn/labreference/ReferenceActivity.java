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
                "(async function() {" +
                "const state=" + state + ";" +
                "const bodyText=()=>document.body ? document.body.innerText.replace(/\\s+/g,' ').trim() : '';" +
                "const report=(ok,reason)=>{" +
                "const details=JSON.stringify({title:document.title,width:innerWidth,height:innerHeight,dpr:devicePixelRatio,scrollY,reason:reason||'',body:bodyText().slice(0,1200),buttons:Array.from(document.querySelectorAll('button')).map(b=>b.innerText.replace(/\\s+/g,' ').trim()).filter(Boolean).slice(0,40)});" +
                "if(ok) window.KellvynLab.ready(state,details); else window.KellvynLab.failed(state,reason||'unknown');" +
                "};" +
                "const waitFor=async predicate=>{const deadline=Date.now()+10000;while(Date.now()<deadline){const value=predicate();if(value)return value;await new Promise(r=>setTimeout(r,150));}return null;};" +
                "const done=()=>report(true,'');" +
                // Use the actual React callback in the lab WebView. The HTMLElement.click()
                // automation did not reliably reach React's delegated handler in headless AVD.
                "const invokeReactClick=(el)=>{const key=Object.keys(el).find(k=>k.startsWith('__reactProps$'));if(key&&typeof el[key].onClick==='function'){el[key].onClick({currentTarget:el,target:el,preventDefault(){},stopPropagation(){}});return 'react';}el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,view:window}));return 'dom';};" +
                // Wait for the React bootstrap effect: it creates kv.active only after event
                // handlers are mounted. Without this barrier, an early programmatic click can
                // be swallowed and the main capture can precede the DigitalRain activation.
                "const booted=await waitFor(()=>{try{const b=document.querySelector('button[aria-label=\\\"Configurações\\\"]');const key=b&&Object.keys(b).find(k=>k.startsWith('__reactProps$'));return !!localStorage.getItem('kv.active') && !!(key&&typeof b[key].onClick==='function');}catch(e){return false;}});" +
                "if(!booted){report(false,'web app did not finish React bootstrap');return 'web-bootstrap-timeout';}" +
                "await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));" +
                "if(state==='main'){done();return 'main-ready';}" +
                "const settings=document.querySelector('button[aria-label=\\\"Configurações\\\"]');" +
                "if(!settings){report(false,'settings button missing');return 'settings-open-failed';}" +
                "invokeReactClick(settings);" +
                "const title=await waitFor(()=>Array.from(document.querySelectorAll('h2')).find(h=>h.innerText.trim().toUpperCase()==='CONFIGURAÇÕES DO KELLVYN'));" +
                "if(!title){report(false,'settings panel did not become visible after click');return 'settings-panel-missing';}" +
                "if(state==='settings'){done();return 'settings-ready';}" +
                "if(state==='gold-settings'||state==='gold-main'){" +
                "const gold=await waitFor(()=>Array.from(document.querySelectorAll('button')).find(b=>b.innerText.replace(/\\s+/g,' ').trim().includes('Preto e Dourado')));" +
                "if(!gold){report(false,'gold palette button missing after settings panel opened');return 'gold-button-missing';}" +
                "gold.scrollIntoView({block:'center'});invokeReactClick(gold);" +
                "const persisted=await waitFor(()=>{try{const p=JSON.parse(localStorage.getItem('kv.settings')||'{}');return p.color?.toUpperCase()==='#D4AF37'&&p.bg?.toUpperCase()==='#0A0907';}catch(e){return false;}});" +
                "if(!persisted){report(false,'gold palette tap did not persist expected colors');return 'gold-palette-not-persisted';}" +
                "if(state==='gold-main'){" +
                "const close=await waitFor(()=>document.querySelector('button[aria-label=\\\"Fechar\\\"]'));" +
                "if(!close){report(false,'settings close button missing after gold palette');return 'settings-close-missing';}" +
                "invokeReactClick(close);" +
                "const closed=await waitFor(()=>!Array.from(document.querySelectorAll('h2')).some(h=>h.innerText.trim().toUpperCase()==='CONFIGURAÇÕES DO KELLVYN'));" +
                "if(!closed){report(false,'settings panel did not close after gold palette');return 'settings-panel-stuck';}" +
                "}" +
                "done();return state+'-ready';" +
                "}" +
                "if(state==='effects-settings'||state==='effects-main'){" +
                "const lightning=await waitFor(()=>Array.from(document.querySelectorAll('button')).find(b=>b.innerText.trim()==='Raios'));" +
                "if(!lightning){report(false,'lightning effect button missing');return 'lightning-button-missing';}" +
                "const already=(()=>{try{const p=JSON.parse(localStorage.getItem('kv.settings')||'{}');return Array.isArray(p.effect)&&p.effect.includes('chuva')&&p.effect.includes('raios');}catch(e){return false;}})();" +
                "if(!already){lightning.scrollIntoView({block:'center'});invokeReactClick(lightning);}" +
                "const both=await waitFor(()=>{try{const p=JSON.parse(localStorage.getItem('kv.settings')||'{}');return Array.isArray(p.effect)&&p.effect.includes('chuva')&&p.effect.includes('raios');}catch(e){return false;}});" +
                "if(!both){report(false,'rain and lightning were not both persisted');return 'rain-lightning-not-persisted';}" +
                "if(state==='effects-main'){" +
                "const close=await waitFor(()=>document.querySelector('button[aria-label=\\\"Fechar\\\"]'));" +
                "if(!close){report(false,'settings close button missing after enabling lightning');return 'effects-close-missing';}" +
                "invokeReactClick(close);" +
                "const closed=await waitFor(()=>!Array.from(document.querySelectorAll('h2')).some(h=>h.innerText.trim().toUpperCase()==='CONFIGURAÇÕES DO KELLVYN'));" +
                "if(!closed){report(false,'settings panel did not close after enabling lightning');return 'effects-panel-stuck';}" +
                "await new Promise(resolve=>setTimeout(resolve,1200));" +
                "}" +
                "done();return state+'-ready';" +
                "}" +
                "report(false,'unsupported lab state '+state);return 'unsupported-state';" +
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
